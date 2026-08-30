"""
Распознавание чертежа (фото) → JSON.
Gemini: не подставлять LLM_MODEL (groq/qwen).
"""

from __future__ import annotations

import base64
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from .schema import FEATURE_SCHEMA_TEXT

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# Актуальные имена (2026): 2.0-flash снят → 3.6-flash
_DEFAULT_GEMINI = "gemini-3.6-flash"
_GEMINI_FALLBACKS = (
    "gemini-3.6-flash",
    "gemini-3.0-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
)
_DEFAULT_OPENROUTER_VISION = "openai/gpt-4o-mini"

_VISION_PROMPT = f"""Ты инженер-конструктор. По изображению чертежа извлеки геометрию.
Ответь ТОЛЬКО валидным JSON без markdown, по схеме:

{FEATURE_SCHEMA_TEXT}

Правила:
- единицы mm
- в hole params — diameter (не радиус)
- нечитаемое → unknown_dimensions
- confidence 0..1
"""


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
        raise ValueError(f"Не JSON из vision:\n{text[:500]}")


def _gemini_candidates() -> List[str]:
    vm = (os.getenv("VISION_MODEL") or "").strip()
    ordered: List[str] = []
    if vm and "gemini" in vm.lower():
        ordered.append(vm)
    for m in _GEMINI_FALLBACKS:
        if m not in ordered:
            ordered.append(m)
    return ordered


def _analyze_gemini(image_bytes: bytes, mime: str) -> Dict[str, Any]:
    import google.generativeai as genai

    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY пуст")
    genai.configure(api_key=key)

    last_err: Optional[Exception] = None
    for model_name in _gemini_candidates():
        try:
            model = genai.GenerativeModel(model_name)
            resp = model.generate_content(
                [
                    _VISION_PROMPT,
                    {"mime_type": mime, "data": image_bytes},
                ],
                generation_config={"temperature": 0.1},
            )
            text = getattr(resp, "text", None) or ""
            return _extract_json(text)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            # пробуем следующую модель при 404 / not available
            if "404" in msg or "no longer available" in msg or "not found" in msg:
                continue
            raise RuntimeError(f"Gemini [{model_name}]: {e}") from e

    raise RuntimeError(
        f"Gemini: ни одна модель не ответила. Последняя ошибка: {last_err}. "
        f"Пробовали: {', '.join(_gemini_candidates())}"
    )


def _openrouter_model_name() -> str:
    vm = (os.getenv("VISION_MODEL") or "").strip()
    if vm and "gemini" not in vm.lower() and "qwen" not in vm.lower():
        if "/" in vm or vm.startswith("openai"):
            return vm
    return _DEFAULT_OPENROUTER_VISION


def _analyze_openrouter(image_bytes: bytes, mime: str) -> Dict[str, Any]:
    from openai import OpenAI

    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY не задан (fallback)")
    model = _openrouter_model_name()
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:{mime};base64,{b64}"
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.1,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _VISION_PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    )
    text = resp.choices[0].message.content or ""
    return _extract_json(text)


def _guess_mime(path: Path) -> str:
    ext = path.suffix.lower()
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(ext, "image/jpeg")


def analyze_drawing(
    image_path: str | Path,
    *,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    data = path.read_bytes()
    mime = _guess_mime(path)
    order = (provider or os.getenv("VISION_PROVIDER", "auto")).lower().strip() or "auto"

    errors: List[str] = []
    if order in ("auto", "gemini"):
        try:
            return _analyze_gemini(data, mime)
        except Exception as e:
            errors.append(f"gemini: {e}")
            if order == "gemini":
                raise RuntimeError(f"Vision Gemini не удался. {e}") from e
    if order in ("auto", "openrouter"):
        try:
            return _analyze_openrouter(data, mime)
        except Exception as e:
            errors.append(f"openrouter: {e}")
            if order == "openrouter":
                raise
    raise RuntimeError("Vision не удался. " + "; ".join(errors))
