"""Drawing vision: image -> validated canonical CAD contract."""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from .contract import normalize_spec
from .contract_validate import validate_contract
from .schema import FEATURE_SCHEMA_TEXT

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

_GEMINI_FALLBACKS = (
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-3.5-flash",
    "gemini-2.5-flash",
)
_DEFAULT_OPENROUTER_VISION = "openai/gpt-4o-mini"
_SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp"}

_VISION_PROMPT = f"""You are a mechanical design engineer reading a manufacturing drawing.
Convert the image into a precise, machine-readable CAD contract.
Return ONLY one JSON object. No markdown, no commentary.

SCHEMA:
{FEATURE_SCHEMA_TEXT}

IMPORTANT INTERPRETATION RULES:
- Thick continuous lines = visible solid geometry.
- Dashed lines = hidden geometry only. Do NOT create an outer wall from them.
- Centerlines / chain lines = axes, symmetry, PCD references; never solid geometry.
- Thin dimension lines = measurements, not geometry.
- Repeated identical holes must be represented as pattern_holes with count + PCD where the drawing supports it.
- Different hole diameters/locations are separate features.
- Counterbore and countersink must preserve pilot diameter, larger diameter and depth when readable.
- A stepped shaft/plug/fitting must describe its cylindrical sections, shoulders and axial lengths explicitly; code generation MUST prefer one longitudinal half-profile + revolve for a turned axisymmetric body.
- Never replace a cylindrical stepped part by a rectangle.
- Build order must be explicit: base -> added material -> cuts -> patterns -> chamfer/fillet.
- Every feature in the drawing that matters to the solid model must appear in features and build_plan.
- All dimensions are millimetres. Never invent an unreadable value. Put it in unknown_dimensions and warnings instead.
- For each build_plan step prefer an object: {{"id":"S01","type":"...","params":{{...}},"depends_on":"S00"}}.
- For each feature prefer an object: {{"id":"F01","type":"...","params":{{...}},"depends_on":"F00"}}.
"""


def _extract_json(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    if not raw:
        raise ValueError("Vision returned an empty response")
    raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```\s*$", "", raw)
    try:
        value = json.loads(raw)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError as first_error:
        decoder = json.JSONDecoder()
        for idx, char in enumerate(raw):
            if char != "{":
                continue
            try:
                value, _ = decoder.raw_decode(raw[idx:])
                if isinstance(value, dict):
                    return value
            except json.JSONDecodeError:
                continue
        raise ValueError(f"Vision JSON parse failed: {first_error}: {raw[:600]}") from first_error
    raise ValueError("Vision JSON root must be an object")


def _gemini_candidates() -> List[str]:
    requested = (os.getenv("VISION_MODEL") or "").strip()
    ordered: List[str] = []
    if requested and requested.lower().startswith("gemini"):
        ordered.append(requested)
    for name in _GEMINI_FALLBACKS:
        if name not in ordered:
            ordered.append(name)
    return ordered


def _analyze_gemini(image_bytes: bytes, mime: str) -> Dict[str, Any]:
    from google import genai
    from google.genai import types

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is not set")
    client = genai.Client(api_key=key)
    last_err: Optional[Exception] = None
    for model_name in _gemini_candidates():
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)
            response = client.models.generate_content(
                model=model_name,
                contents=[_VISION_PROMPT, image_part],
                config=types.GenerateContentConfig(
                    temperature=0.0,
                    response_mime_type="application/json",
                    max_output_tokens=12000,
                ),
            )
            text = getattr(response, "text", None) or ""
            if text.strip():
                return _extract_json(text)
            raise RuntimeError("empty response")
        except Exception as exc:
            last_err = exc
            msg = str(exc).lower()
            if any(x in msg for x in ("404", "not found", "no longer available", "unsupported", "429", "quota", "rate limit", "resource exhausted")):
                continue
            raise RuntimeError(f"Gemini [{model_name}]: {exc}") from exc
    raise RuntimeError(f"Gemini models unavailable; last={last_err}")


def _analyze_openrouter(image_bytes: bytes, mime: str) -> Dict[str, Any]:
    from openai import OpenAI

    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")
    requested = (os.getenv("VISION_MODEL") or "").strip()
    model = requested if requested and "gemini" not in requested.lower() else _DEFAULT_OPENROUTER_VISION
    b64 = base64.b64encode(image_bytes).decode("ascii")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    response = client.chat.completions.create(
        model=model,
        temperature=0.0,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": _VISION_PROMPT},
                {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}},
            ],
        }],
    )
    text = getattr(response.choices[0].message, "content", None) or ""
    return _extract_json(text)


def _guess_mime(path: Path) -> str:
    return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}.get(path.suffix.lower(), "")


def analyze_drawing(image_path: str | Path, *, provider: Optional[str] = None) -> Dict[str, Any]:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    data = path.read_bytes()
    if len(data) < 256:
        raise RuntimeError("Image is empty or too small")
    mime = _guess_mime(path)
    if mime not in _SUPPORTED_MIME:
        raise RuntimeError(f"Unsupported drawing image format: {path.suffix or '<none>'}")

    order = (provider or os.getenv("VISION_PROVIDER", "auto")).lower().strip() or "auto"
    errors: List[str] = []
    providers = [order] if order != "auto" else ["gemini", "openrouter"]
    for current in providers:
        try:
            raw = _analyze_gemini(data, mime) if current == "gemini" else _analyze_openrouter(data, mime)
            spec = normalize_spec(raw)
            hard, warnings = validate_contract(spec)
            if hard:
                raise RuntimeError("Invalid vision contract: " + "; ".join(hard[:8]))
            if warnings:
                spec["warnings"] = list(dict.fromkeys((spec.get("warnings") or []) + warnings))[:20]
            if not spec.get("features") and not spec.get("build_plan"):
                raise RuntimeError("Vision returned no build features")
            return spec
        except Exception as exc:
            errors.append(f"{current}: {exc}")
    raise RuntimeError("Vision failed: " + " | ".join(errors))
