"""
Проверка кода ДО запуска в КОМПАС.
1) структура  2) опционально LLM-критик
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

KNOWN_PART_METHODS = frozenset(
    {
        "create",
        "from_active",
        "sketch",
        "sketch_on_face",
        "extrude",
        "cut",
        "revolve",
        "get_edges",
        "chamfer",
        "fillet",
        "fillet_edge",
        "chamfer_edge",
        "hole",
        "pattern_holes_circular",
        "pattern_holes_rect",
        "pattern_holes_points",
        "pattern_holes_linear",
        "hole_list",
        "mirror_points",
        "slot",
        "step",
        "boss",
        "hex_boss",
        "ring_groove",
        "groove",
        "keyway",
        "pocket",
        "counterbore",
        "countersink",
        "export",
        "export_formats",
        "close",
        "mass_properties",
        "update",
        "shell",
        "thread",
    }
)

_FORBIDDEN = (
    "win32com",
    "gencache",
    "Dispatch",
    "GetActiveObject",
    "loft(",
    "sweep(",
)


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
            "штуцер",
            "шестигран",
            "канавк",
            "карман",
            "бобыш",
            "feature=",
            "build_plan",
            "body_style=cylindrical",
            "required_features=",
        )
    ):
        return True
    if re.search(r"\bвал\b", t):
        return True
    diams = re.findall(r"(?:ø|∅|diameter\s*=)\s*(\d+)", t)
    return len(set(diams)) >= 2


def extract_part_calls(code: str) -> List[str]:
    return re.findall(r"\bpart\.([A-Za-z_]\w*)\s*\(", code or "")


def unknown_part_calls(code: str) -> List[str]:
    return list(
        dict.fromkeys(
            n for n in extract_part_calls(code) if n not in KNOWN_PART_METHODS
        )
    )


def summarize_ops(code: str) -> Dict[str, int]:
    c = code or ""
    keys = (
        "extrude(",
        "cut(",
        "hole(",
        "pattern_holes",
        "circle(",
        "rectangle(",
        "rounded_rect(",
        "polygon(",
        "fillet(",
        "chamfer(",
        "boss(",
        "step(",
        "slot(",
        "pocket(",
        "counterbore(",
        "ring_groove(",
    )
    return {k.rstrip("("): c.lower().count(k.lower()) for k in keys}


def review_structure(task: str, code: str) -> List[str]:
    issues: List[str] = []
    t = _low(task)
    c = _low(code)
    if not c.strip():
        return ["пустой код"]

    # не смотреть boilerplate
    t_lines = [
        ln
        for ln in t.splitlines()
        if not ln.strip().startswith("ops_order=")
        and not ln.strip().startswith("правило:")
        and not ln.strip().startswith("порядок:")
    ]
    t = "\n".join(t_lines)

    n_ext = c.count("extrude(")
    n_cut = c.count("cut(")
    n_hole = c.count("hole(") + c.count("pattern_holes")
    n_circ = c.count("circle(")
    n_rect = c.count("rectangle(")
    n_poly = c.count("polygon(")

    unknown = unknown_part_calls(code)
    if unknown:
        issues.append("неизвестные part." + ", part.".join(unknown) + " (нет в core)")

    for bad in _FORBIDDEN:
        if bad.lower() in c:
            issues.append(f"запрещённый фрагмент: {bad}")

    cylindrical = (
        "body_style=cylindrical" in t
        or any(w in t for w in ("пробк", "штуцер", "shaft", "втулк", "цилиндр"))
        or re.search(r"\bвал\b", t) is not None
        or (len(re.findall(r"(?:ø|∅)\s*\d+", t)) >= 2)
    )
    if cylindrical and n_rect > 0 and n_circ == 0:
        issues.append(
            "для цилиндрической/ступенчатой детали использован rectangle — нужны circle+extrude"
        )
    if cylindrical and n_ext < 2 and any(
        w in t for w in ("ступен", "уступ", "пробк", "feature=step", "feature=boss")
    ):
        issues.append("мало extrude для ступенчатой детали (ожидается ≥2)")

    if (
        any(w in t for w in ("карман", "углублен", "шестигранн", "выборк"))
        or "feature=pocket" in t
        or "feature=hex_pocket" in t
    ):
        if n_cut == 0 and n_hole == 0 and "pocket(" not in c:
            issues.append("нужен cut/hole/pocket для кармана или углубления")
        if ("шестигран" in t or "hex_pocket" in t) and n_poly == 0 and "hex_" not in c:
            if n_cut == 0 and "pocket(" not in c:
                issues.append("шестигранник: polygon/hex_boss/pocket + cut")

    if ("feature=groove" in t or "канавк" in t) and "ring_groove(" not in c and "groove(" not in c:
        if not (n_circ >= 2 and n_cut >= 1):
            issues.append("канавка: ring_groove или два circle + cut")

    if any(w in t for w in ("отверст", "крепеж")) or "feature=hole" in t or "feature=pattern_holes" in t:
        if n_hole == 0 and n_cut == 0:
            issues.append("в ТЗ отверстия, в коде нет hole/cut/pattern_holes")

    if re.search(r"chamfer\s*\(\s*size\s*=", c):
        issues.append(
            "chamfer(size=...): part.chamfer(edges, distance=...) или part.chamfer(distance)"
        )

    if "part.update(" not in c:
        issues.append("нет part.update()")

    if n_rect and not n_circ and (
        cylindrical or any(w in t for w in ("ø", "диаметр", "ступен", "бобыш", "пробк"))
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
        if re.search(r"\bok\b\s*[:=]\s*true", text, re.I):
            return {"ok": True, "issues": []}
        return {"ok": False, "issues": ["критик не вернул JSON"]}


def llm_review(llm: Any, task: str, code: str) -> List[str]:
    prompt = (
        "Ты проверяешь Python-код для КОМПАС (core API) ДО выполнения.\n"
        "Ответь ТОЛЬКО JSON: {\"ok\": true/false, \"issues\": [\"...\"]}\n"
        "ok=true только если код строит ВСЮ геометрию из ТЗ.\n"
        "Не пиши код.\n\n"
        f"ТЗ:\n{task[:2000]}\n\n"
        f"Код:\n```python\n{code[:3500]}\n```\n"
    )
    try:
        raw = llm.chat(
            [
                {"role": "system", "content": "CAD code reviewer. JSON only."},
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
    except Exception:
        return []


def review_before_build(
    task: str,
    code: str,
    *,
    llm: Any = None,
    use_llm: Optional[bool] = None,
) -> Tuple[bool, List[str]]:
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
