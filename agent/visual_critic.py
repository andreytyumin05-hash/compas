"""Visual critic for post-build KOMPAS verification.

The critic treats screenshots as evidence, not as proof by themselves. It can
consume up to three complementary views and optional feature-tree context.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Mapping, Sequence

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")
log = logging.getLogger("compas.visual_critic")

_PROMPT = """You are a CAD quality-control engineer for KOMPAS-3D.
Inspect the supplied screenshots and optional feature-tree state against the task.
Return ONLY JSON: {"ok": true|false, "issues": ["short issue"]}.
Treat a green execution result as insufficient evidence. Check whether the visible
shape, number/location of openings, steps, grooves, pockets, boss geometry and
orientation match the task. Use the top/front/iso views together. Do not invent
missing geometry from imagination. Maximum 6 issues.
"""


def _parse(text: str) -> Dict[str, Any]:
    raw = (text or "").strip()
    raw = re.sub(r"^\s*```(?:json)?\s*", "", raw, flags=re.I)
    raw = re.sub(r"\s*```\s*$", "", raw)
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {"ok": False, "issues": ["critic returned non-object JSON"]}
    except json.JSONDecodeError:
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
    if re.search(r"\bok\b\s*[:=]\s*true", raw, re.I):
        return {"ok": True, "issues": []}
    return {"ok": False, "issues": ["visual critic returned invalid JSON"]}


def _prompt(task: str, code: str, images: Sequence[Path], context: Mapping[str, Any] | None) -> tuple[str, List[Any]]:
    text = _PROMPT + f"\n\nTASK:\n{task[:2500]}\n\nSCRIPT:\n{(code or '')[:3500]}\n"
    if context:
        text += "\nFEATURE TREE / STATE:\n" + str(context)[:5000]
    parts: List[Any] = [text]
    for path in images[:3]:
        try:
            data = path.read_bytes()
            if len(data) < 80:
                continue
            mime = "image/jpeg" if path.suffix.lower() in {".jpg", ".jpeg"} else "image/png"
            parts.append((mime, data))
        except OSError:
            continue
    return text, parts


def _gemini_review(task: str, code: str, images: Sequence[Path], context: Mapping[str, Any] | None) -> List[str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return []
    prompt, parts = _prompt(task, code, images, context)
    if len(parts) < 2:
        return []
    models = [
        (os.getenv("VISION_MODEL") or "").strip(),
        "gemini-3.7-flash",
        "gemini-3.6-flash",
        "gemini-2.5-flash",
    ]
    models = list(dict.fromkeys(x for x in models if x))
    try:
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=key)
        last: Exception | None = None
        for model_name in models:
            try:
                content = [prompt]
                for mime, data in parts[1:]:
                    content.append(types.Part.from_bytes(data=data, mime_type=mime))
                response = client.models.generate_content(
                    model=model_name,
                    contents=content,
                    config=types.GenerateContentConfig(
                        temperature=0.0,
                        response_mime_type="application/json",
                        max_output_tokens=900,
                    ),
                )
                data = _parse(getattr(response, "text", None) or "")
                if data.get("ok") is True:
                    return []
                issues = data.get("issues") or []
                if isinstance(issues, str):
                    issues = [issues]
                return [str(x) for x in issues if str(x).strip()][:6]
            except Exception as exc:
                last = exc
                if any(s in str(exc).lower() for s in ("404", "not found", "unsupported")):
                    continue
                if any(s in str(exc).lower() for s in ("429", "quota", "rate limit", "resource exhausted")):
                    continue
        if last:
            log.warning("Gemini visual critic failed: %s", last)
    except ImportError:
        pass
    return []


def _openrouter_review(task: str, code: str, images: Sequence[Path], context: Mapping[str, Any] | None) -> List[str]:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return []
    _, parts = _prompt(task, code, images, context)
    if len(parts) < 2:
        return []
    try:
        from openai import OpenAI
    except ImportError:
        return []
    content: List[Dict[str, Any]] = [{"type": "text", "text": str(parts[0])}]
    for mime, data in parts[1:]:
        b64 = base64.b64encode(data).decode("ascii")
        content.append({"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}})
    model = (os.getenv("OPENROUTER_VISION_MODEL") or "openai/gpt-4o-mini").strip()
    try:
        response = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key).chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            temperature=0.0,
            max_tokens=600,
        )
        data = _parse((response.choices[0].message.content or "") if response.choices else "")
        if data.get("ok") is True:
            return []
        issues = data.get("issues") or []
        if isinstance(issues, str):
            issues = [issues]
        return [str(x) for x in issues if str(x).strip()][:6]
    except Exception as exc:
        log.warning("OpenRouter visual critic failed: %s", exc)
        return []


def review_screenshots(
    task: str,
    code: str,
    image_paths: Sequence[str | Path],
    *,
    context: Mapping[str, Any] | None = None,
) -> List[str]:
    paths = [Path(p) for p in image_paths if p and Path(p).exists()]
    paths = [p for p in paths if p.stat().st_size > 80]
    if not paths:
        return []
    issues = _gemini_review(task, code, paths, context)
    if issues:
        return issues
    return _openrouter_review(task, code, paths, context)
