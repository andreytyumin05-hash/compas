"""
Проверка кода ДО запуска в КОМПАС.

1) Детерминированный разбор структуры (быстро, бесплатно)
2) Для сложных ТЗ — короткий LLM-критик (переделка, если коряво)
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple


def _low(s: str) -> str:
    return (s or "").lower()


def is_complex_task(task: str) -> bool:
    t = _low(task)
    if any(
        w in t
        for w in (
            "ступен",
            "уступ",
            "пробк",
            "вал",
            "штуцер",
            "шестигран",
            "канавк",
            "карман",
            "бобыш",
            "feature=",
            "feature_order",
        )
    ):
        return True
    diams = re.findall(r"(?:ø|∅|diameter\s*=|диаметр)\s*(\d+)", t)
    return len(set(diams)) >= 2


def review_structure(task: str, code: str) -> List[str]:
    """Эвристики «код выглядит как неправильная деталь»."""
    issues: List[str] = []
    t = _low(task)
    c = _low(code)
    if not c.strip():
        return ["пустой код"]

    n_ext = c.count("extrude(")
    n_cut = c.count("cut(")
    n_hole = c.count("hole(") + c.count("pattern_holes")
    n_circ = c.count("circle(")
    n_rect = c.count("rectangle(")
    n_poly = c.count("polygon(")

    # Вал / пробка / штуцер — не параллелепипед
    cylindrical = any(
        w in t for w in ("пробк", "вал", "штуцер", "shaft", "втулк", "цилиндр")
    ) or (len(re.findall(r"(?:ø|∅)\s*\d+", t)) >= 2)
    if cylindrical and n_rect > 0 and n_circ == 0:
        issues.append(
            "для цилиндрической/ступенчатой детали использован rectangle — нужны circle+extrude"
        )
    if cylindrical and n_ext < 2 and any(
        w in t for w in ("ступен", "уступ", "пробк", "канал", "стержен")
    ):
        issues.append("мало extrude для ступенчатой детали (ожидается ≥2)")

    # Карман / шестигранник / углубление → cut или hole, не только extrude
    if any(w in t for w in ("карман", "углублен", "шестигранн", "выборк")):
        if n_cut == 0 and n_hole == 0:
            issues.append("нужен cut/hole для кармана или углубления, не только extrude")
        if "шестигран" in t and n_poly == 0 and "polygon" not in c:
            # иногда hole круглый — мягко
            if n_cut == 0:
                issues.append("шестигранник: ожидается polygon + cut(depth=...)")

    # Вырез через «лишний extrude» без cut при словах вырез/карман
    if any(w in t for w in ("вырез", "карман", "глух")) and n_cut == 0 and n_ext >= 1:
        if "through_all" not in c and "hole(" not in c:
            issues.append("вырез описан в ТЗ, но в коде нет cut/hole")

    # Отверстия в ТЗ
    if any(w in t for w in ("отверст", "крепеж")) and n_hole == 0 and n_cut == 0:
        issues.append("в ТЗ отверстия, в коде нет hole/cut/pattern_holes")

    # Фаска/скругление API
    if "fillet(" in c and "get_edges" not in c:
        issues.append("fillet без get_edges — вызов, скорее всего, неверный")
    if "chamfer(" in c and "get_edges" not in c:
        issues.append("chamfer без get_edges — вызов, скорее всего, неверный")
    if re.search(r"fillet\s*\(\s*radius\s*=", c) or re.search(
        r"chamfer\s*\(\s*size\s*=", c
    ):
        issues.append("fillet/chamfer: нужен part.fillet(edges, radius=...) / chamfer(edges, distance=...)")

    # Запрещённые «методы»
    for bad in ("part.step(", "part.slot(", "win32com", "loft(", "sweep("):
        if bad in c:
            issues.append(f"запрещённый вызов: {bad}")

    # Нет update
    if "part.update(" not in c:
        issues.append("нет part.update()")

    # Один rectangle на «богатом» ТЗ
    if n_rect and not n_circ and any(
        w in t for w in ("ø", "диаметр", "ступен", "бобыш", "пробк")
    ):
        issues.append("код похож на плиту, а ТЗ описывает круглую/ступенчатую геометрию")

    return list(dict.fromkeys(issues))


def _parse_critic_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            return json.loads(m.group(0))
        # fallback: ищем ok/false
        if re.search(r"\bok\b\s*[:=]\s*true", text, re.I):
            return {"ok": True, "issues": []}
        return {"ok": False, "issues": ["критик не вернул JSON"]}


def llm_review(llm: Any, task: str, code: str) -> List[str]:
    """Короткий отзыв модели: ok или список проблем (не новый код)."""
    prompt = (
        "Ты проверяешь Python-код для КОМПАС (core API) ДО выполнения.\n"
        "Ответь ТОЛЬКО JSON: {\"ok\": true/false, \"issues\": [\"...\"]}\n"
        "ok=true только если код реально строит ВСЮ геометрию из ТЗ\n"
        "(ступени, вырезы cut а не лишний extrude, отверстия, без rectangle вместо цилиндров).\n"
        "Не пиши код.\n\n"
        f"ТЗ:\n{task[:2000]}\n\n"
        f"Код:\n```python\n{code[:3500]}\n```\n"
    )
    try:
        raw = llm.chat(
            [
                {
                    "role": "system",
                    "content": "CAD code reviewer. JSON only.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        data = _parse_critic_json(raw or "")
        if data.get("ok") is True:
            return []
        issues = data.get("issues") or []
        if isinstance(issues, str):
            issues = [issues]
        return [str(x) for x in issues if str(x).strip()][:8]
    except Exception as e:
        # критик не должен ломать пайплайн
        return []


def review_before_build(
    task: str,
    code: str,
    *,
    llm: Any = None,
    use_llm: Optional[bool] = None,
) -> Tuple[bool, List[str]]:
    """
    Полная проверка перед КОМПАС.
    use_llm: None = автоматически для сложных ТЗ если structure уже ок
             (второй взгляд) или если structure нашёл проблемы — LLM не обязателен
    """
    structural = review_structure(task, code)
    if structural:
        return False, structural

    if use_llm is None:
        use_llm = is_complex_task(task)

    if use_llm and llm is not None:
        llm_issues = llm_review(llm, task, code)
        if llm_issues:
            return False, llm_issues

    return True, []
