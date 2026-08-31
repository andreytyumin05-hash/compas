"""Распознавание чертежа → JSON + план построения."""

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

_GEMINI_FALLBACKS = (
    "gemini-3.6-flash",
    "gemini-3.0-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
    "gemini-pro-latest",
)
_DEFAULT_OPENROUTER_VISION = "openai/gpt-4o-mini"

_VISION_PROMPT = f"""Ты инженер-конструктор с опытом чтения машиностроительных чертежей.
По изображению извлеки геометрию и КАК лучше собрать деталь в CAD.
Ответ — ТОЛЬКО один JSON без markdown.

Схема:
{FEATURE_SCHEMA_TEXT}

## Чтение линий (критично)
- Сплошная толстая — видимый контур → тело / ступень / бобышка (extrude).
- Штриховая (пунктир) — скрытый контур за телом → отверстие, полость, дальняя кромка.
  НЕ делай из пунктира наружную стенку и НЕ выдавливай как основной контур.
- Штрихпунктирная — ось, PCD, плоскость симметрии → для массивов и центров, не контур.
- Тонкая сплошная — размерные / вспомогательные — только размеры, не геометрия.

## Паттерны
- Одинаковые отверстия по кругу → type=pattern_holes, pattern=circular, pcd, count, diameter.
- По прямой → pattern=linear.
- Разные диаметры в разных местах → отдельные hole / hole_list, не один «усреднённый».
- Цековка / зенковка: counterbore / countersink (pilot + больший диаметр + depth).

## Ступени и тела
- Каждая цилиндрическая ступень со своим Ø и длиной — отдельный feature step/extrude_body.
- Не склеивай вал/пробку/штуцер в одну «плиту» или один rectangle.
- part_type: shaft|plug для осевых ступенчатых; cover|flange для плоских с бобышкой.

## build_plan
Обязательно заполни build_plan — нумерованные шаги для CAD-агента, например:
1. База Ø50 L10 circle+extrude
2. Ступень Ø42 L20
3. Канавка ring_groove
4. Шестигранный карман polygon+cut
5. pattern_holes_circular …
6. chamfer на торце
Укажи depends_on, если шаг опирается на предыдущий.

## Размеры
- mm; у отверстий diameter (не радиус).
- Не выдумывай; нечитаемое → unknown_dimensions + warnings.
- patterns_hint: короткие фразы «N×Ød на PCD …».
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
        raise RuntimeError("GEMINI_API_KEY пуст — vision не работает")
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
                generation_config={"temperature": 0.15},
            )
            text = getattr(resp, "text", None) or ""
            if not text.strip():
                raise RuntimeError("пустой ответ Gemini")
            return _extract_json(text)
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            if "404" in msg or "no longer available" in msg or "not found" in msg:
                continue
            raise RuntimeError(f"Gemini [{model_name}]: {e}") from e

    raise RuntimeError(
        f"Gemini: ни одна модель. last={last_err}. "
        f"Пробовали: {', '.join(_gemini_candidates())}"
    )


def _analyze_openrouter(image_bytes: bytes, mime: str) -> Dict[str, Any]:
    from openai import OpenAI

    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY не задан")
    vm = (os.getenv("VISION_MODEL") or "").strip()
    model = (
        vm if vm and "gemini" not in vm.lower() else _DEFAULT_OPENROUTER_VISION
    )
    b64 = base64.b64encode(image_bytes).decode("ascii")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=key)
    resp = client.chat.completions.create(
        model=model,
        temperature=0.15,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": _VISION_PROMPT},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                ],
            }
        ],
    )
    text = resp.choices[0].message.content or ""
    return _extract_json(text)


def _guess_mime(path: Path) -> str:
    return {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/jpeg")


def analyze_drawing(
    image_path: str | Path,
    *,
    provider: Optional[str] = None,
) -> Dict[str, Any]:
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(str(path))
    data = path.read_bytes()
    if len(data) < 100:
        raise RuntimeError("Файл картинки пустой или слишком маленький")
    mime = _guess_mime(path)
    order = (provider or os.getenv("VISION_PROVIDER", "auto")).lower().strip() or "auto"

    errors: List[str] = []
    if order in ("auto", "gemini"):
        try:
            return _analyze_gemini(data, mime)
        except Exception as e:
            errors.append(f"gemini: {e}")
            if order == "gemini":
                raise RuntimeError(f"Vision: {e}") from e
    if order in ("auto", "openrouter"):
        try:
            return _analyze_openrouter(data, mime)
        except Exception as e:
            errors.append(f"openrouter: {e}")
            if order == "openrouter":
                raise
    raise RuntimeError("Vision не удался. " + "; ".join(errors))
