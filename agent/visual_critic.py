"""
VLM-критик после построения (Habr visual loop).

Берёт 1–2 скриншота модели + ТЗ → JSON {ok, issues}.
Без ключа / без файлов — пустой список issues (не ломает build).
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

log = logging.getLogger("compas.visual_critic")

_PROMPT = """Ты инженер-контролёр CAD. По скриншотам 3D-модели КОМПАС и ТЗ реши:
соответствует ли модель заданию.

Ответь ТОЛЬКО JSON:
{"ok": true/false, "issues": ["кратко по-русски"]}

ok=true только если видимая геометрия согласуется с ТЗ
(ступени, отверстия, габариты на глаз, нет явной «коробки вместо цилиндра»).
Не пиши код. Не больше 5 issues.
"""


def _parse(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                pass
        if re.search(r"\bok\b\s*[:=]\s*true", text, re.I):
            return {"ok": True, "issues": []}
        return {"ok": False, "issues": ["VLM не вернул JSON"]}


def _gemini_review(task: str, code: str, images: Sequence[Path]) -> List[str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        return []
    try:
        import google.generativeai as genai
    except ImportError:
        return []

    genai.configure(api_key=key)
    parts: List[Any] = [
        _PROMPT
        + f"\n\nТЗ:\n{task[:1500]}\n\nКод (фрагмент):\n{(code or '')[:1200]}\n"
    ]
    for p in images[:3]:
        try:
            data = Path(p).read_bytes()
            if len(data) < 50:
                continue
            mime = "image/png"
            if str(p).lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            parts.append({"mime_type": mime, "data": data})
        except Exception as e:
            log.debug("skip image %s: %s", p, e)

    if len(parts) < 2:
        return []

    models = [
        os.getenv("VISION_MODEL", "").strip() or "gemini-2.5-flash",
        "gemini-2.5-flash",
        "gemini-flash-latest",
        "gemini-1.5-flash",
    ]
    last = ""
    for name in models:
        if not name:
            continue
        try:
            model = genai.GenerativeModel(name)
            resp = model.generate_content(parts)
            last = getattr(resp, "text", None) or str(resp)
            data = _parse(last)
            if data.get("ok") is True:
                return []
            issues = data.get("issues") or []
            if isinstance(issues, str):
                issues = [issues]
            return [str(x) for x in issues if str(x).strip()][:5]
        except Exception as e:
            last = str(e)
            log.warning("visual critic %s: %s", name, e)
            continue
    log.warning("visual critic failed: %s", last[:200])
    return []


def _openrouter_review(task: str, code: str, images: Sequence[Path]) -> List[str]:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        return []
    try:
        from openai import OpenAI
    except ImportError:
        return []

    content: List[Dict[str, Any]] = [
        {
            "type": "text",
            "text": _PROMPT
            + f"\n\nТЗ:\n{task[:1500]}\n\nКод:\n{(code or '')[:1000]}\n",
        }
    ]
    for p in images[:2]:
        try:
            b = Path(p).read_bytes()
            if len(b) < 50:
                continue
            mime = "image/png"
            if str(p).lower().endswith((".jpg", ".jpeg")):
                mime = "image/jpeg"
            b64 = base64.b64encode(b).decode("ascii")
            content.append(
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime};base64,{b64}"},
                }
            )
        except Exception:
            continue
    if len(content) < 2:
        return []

    client = OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    model = os.getenv("OPENROUTER_VISION_MODEL", "openai/gpt-4o-mini")
    try:
        r = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": content}],
            temperature=0.0,
            max_tokens=400,
        )
        text = (r.choices[0].message.content or "") if r.choices else ""
        data = _parse(text)
        if data.get("ok") is True:
            return []
        issues = data.get("issues") or []
        if isinstance(issues, str):
            issues = [issues]
        return [str(x) for x in issues if str(x).strip()][:5]
    except Exception as e:
        log.warning("openrouter visual: %s", e)
        return []


def review_screenshots(
    task: str,
    code: str,
    image_paths: Sequence[str | Path],
) -> List[str]:
    """Список проблем с модели по скриншотам. Пусто = ок или недоступно."""
    paths = [Path(p) for p in image_paths if p and Path(p).exists()]
    # отфильтровать пустые/битые
    paths = [p for p in paths if p.stat().st_size > 80]
    if not paths:
        return []

    issues = _gemini_review(task, code, paths)
    if issues:
        return issues
    # если gemini «молча ок» или нет ключа — пробуем openrouter
    if not os.getenv("GEMINI_API_KEY", "").strip():
        return _openrouter_review(task, code, paths)
    return issues
