"""Схема чертежа: features + план построения для LLM."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

FEATURE_SCHEMA_TEXT = """
{
  "part_type": "bushing|flange|plate|shaft|cover|bracket|plug|other",
  "name": "строка",
  "units": "mm",
  "axis": "Z|X|Y",
  "overall": {
    "width": null, "height": null, "length": null,
    "outer_diameter": null, "inner_diameter": null,
    "thickness": null, "total_height": null
  },
  "drawing": {
    "views": ["main|top|side|section"],
    "solid_lines": "видимый контур детали",
    "dashed_lines": "скрытый контур / оси — НЕ строить как наружную стенку",
    "centerlines": "оси симметрии, PCD",
    "notes": "что пунктир означает на этом чертеже"
  },
  "build_plan": [
    "1. База: ...",
    "2. Ступень: ...",
    "3. Карман/отверстия массивом: ...",
    "4. Фаски: ..."
  ],
  "features": [
    {
      "type": "extrude_body|boss|step|hole|pattern_holes|pocket|hex_pocket|groove|counterbore|countersink|chamfer|fillet|slot|keyway",
      "params": {
        "diameter": null, "length": null, "width": null, "height": null,
        "depth": null, "thickness": null, "pcd": null, "count": null,
        "x": null, "y": null, "shape": null, "through_all": null,
        "pilot_diameter": null, "counterbore_diameter": null,
        "outer_diameter": null, "inner_diameter": null,
        "fillet_radius": null, "chamfer_distance": null,
        "pattern": "circular|linear|points|none"
      },
      "depends_on": "после какой фичи (текстом)",
      "notes": "кратко по-русски"
    }
  ],
  "patterns_hint": [
    "6 отверстий Ø8 на PCD 82 → pattern_holes_circular"
  ],
  "unknown_dimensions": [],
  "warnings": []
}
""".strip()

_TYPE_RU = {
    "bushing": "втулка",
    "flange": "фланец",
    "plate": "плита",
    "shaft": "вал",
    "cover": "крышка",
    "bracket": "кронштейн",
    "plug": "пробка",
    "other": "деталь",
}

_FEAT_RU = {
    "extrude_body": "основное тело",
    "boss": "бобышка",
    "step": "ступень",
    "hole": "отверстие",
    "pattern_holes": "массив отверстий",
    "pocket": "карман",
    "hex_pocket": "шестигранное углубление",
    "groove": "канавка",
    "counterbore": "цековка",
    "countersink": "зенковка",
    "fillet": "скругление",
    "chamfer": "фаска",
    "slot": "паз",
    "keyway": "шпоночный паз",
}


def _num(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        f = float(v)
        if abs(f - int(f)) < 1e-9:
            return str(int(f))
        return f"{f:g}"
    except Exception:
        return str(v)


def _flatten_params(params: Any) -> Dict[str, Any]:
    if not isinstance(params, dict):
        return {}
    out: Dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, (int, float, str, bool)):
            out[str(k)] = v
        elif isinstance(v, dict):
            for k2, v2 in v.items():
                if isinstance(v2, (int, float, str, bool)):
                    out[f"{k}_{k2}"] = v2
    return out


def _feat_human(feat: Dict[str, Any]) -> str:
    ftype = str(feat.get("type") or "")
    title = _FEAT_RU.get(ftype, ftype or "элемент")
    p = _flatten_params(feat.get("params"))
    bits: List[str] = []
    for key, label in (
        ("diameter", "Ø"),
        ("length", "длина"),
        ("width", "ширина"),
        ("height", "высота"),
        ("depth", "глубина"),
        ("thickness", "толщина"),
        ("pcd", "PCD"),
        ("count", "N"),
        ("chamfer_distance", "фаска"),
        ("fillet_radius", "R"),
    ):
        if key in p and p[key] is not None:
            if label == "Ø":
                bits.append(f"Ø{_num(p[key])}")
            elif label in ("PCD", "N", "R"):
                bits.append(f"{label} {_num(p[key])}")
            else:
                bits.append(f"{label} {_num(p[key])} мм")
    if p.get("through_all") in (True, "true", "1"):
        bits.append("сквозное")
    if p.get("pattern") and str(p["pattern"]) != "none":
        bits.append(f"массив {p['pattern']}")
    note = (feat.get("notes") or "").strip()
    if note and len(note) < 90 and "{" not in note:
        bits.append(note)
    return f"• {title}: " + ", ".join(bits) if bits else f"• {title}"


def format_spec_for_user(spec: Dict[str, Any]) -> str:
    units = spec.get("units") or "мм"
    ptype = str(spec.get("part_type") or "other")
    name = spec.get("name") or _TYPE_RU.get(ptype, "деталь")

    lines: List[str] = [
        "Распознал так:",
        "",
        f"Деталь: {name} ({_TYPE_RU.get(ptype, ptype)})",
    ]
    if spec.get("axis"):
        lines.append(f"Ось: {spec['axis']}")

    overall = spec.get("overall") or {}
    dim_bits = []
    if overall.get("length") is not None and overall.get("width") is not None:
        dim_bits.append(
            f"габарит {_num(overall['length'])}×{_num(overall['width'])} {units}"
        )
    for k, lab in (
        ("thickness", "толщина"),
        ("total_height", "общая высота"),
        ("outer_diameter", "Ø нар."),
        ("inner_diameter", "Ø вн."),
        ("length", "длина"),
    ):
        if overall.get(k) is not None and not (
            k == "length" and overall.get("width") is not None
        ):
            dim_bits.append(f"{lab} {_num(overall[k])} {units}")
    if dim_bits:
        lines.append("Размеры: " + "; ".join(dim_bits))

    plan = spec.get("build_plan") or []
    if plan:
        lines.append("")
        lines.append("План построения:")
        for step in plan[:12]:
            s = str(step).strip()
            if s:
                lines.append(f"  {s}" if s[0].isdigit() else f"  • {s}")
    else:
        lines.append("")
        lines.append("Элементы:")
        for f in spec.get("features") or []:
            lines.append(_feat_human(f))

    drawing = spec.get("drawing") or {}
    if drawing.get("dashed_lines") or drawing.get("notes"):
        lines.append("")
        lines.append(
            "Чертёж: пунктир/оси — не наружный контур; "
            + str(drawing.get("notes") or drawing.get("dashed_lines") or "")[:120]
        )

    hints = spec.get("patterns_hint") or []
    if hints:
        lines.append("Массивы: " + "; ".join(str(h)[:80] for h in hints[:4]))

    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("Не прочитано: " + ", ".join(str(u) for u in unk[:8]))

    for w in (spec.get("warnings") or [])[:3]:
        if w and isinstance(w, str):
            lines.append(f"⚠ {w[:120]}")

    lines.append("")
    lines.append("Если верно — «Строить». Если нет — размеры текстом.")
    return "\n".join(lines)


def spec_to_task_text(spec: Dict[str, Any]) -> str:
    """ТЗ для кодогена: план + фичи. Без слов-триггеров в boilerplate."""
    lines: List[str] = []
    ptype = str(spec.get("part_type") or "other")
    name = spec.get("name") or ptype
    lines.append(f"Деталь: {name} (тип {ptype})")
    if spec.get("axis"):
        lines.append(f"axis={spec['axis']}")

    lines.append(
        "Правило: solid_contour=body; dashed/hidden/centerline ≠ наружный контур"
    )

    plan = spec.get("build_plan") or []
    if plan:
        lines.append("BUILD_PLAN:")
        for step in plan:
            lines.append(f"  - {step}")
    else:
        # нейтрально, без «карман/отверстие/фаска» — иначе ложные требования к коду
        lines.append("ops_order=base,add_material,cuts,patterns,edges")

    drawing = spec.get("drawing") or {}
    for k in ("dashed_lines", "centerlines", "notes"):
        if drawing.get(k):
            lines.append(f"drawing_{k}={drawing[k]}")

    overall = spec.get("overall") or {}
    for k, v in overall.items():
        if v is not None:
            lines.append(f"{k}={v}")

    feat_types: List[str] = []
    for feat in spec.get("features") or []:
        ftype = str(feat.get("type") or "")
        if ftype:
            feat_types.append(ftype)
        p = _flatten_params(feat.get("params"))
        lines.append(f"feature={ftype}")
        if feat.get("depends_on"):
            lines.append(f"depends_on={feat['depends_on']}")
        for key, val in p.items():
            if isinstance(val, (int, float, str, bool)) and str(val):
                lines.append(f"{key}={val}")
        if feat.get("notes"):
            lines.append(str(feat["notes"]))

    for h in spec.get("patterns_hint") or []:
        lines.append(f"pattern_hint={h}")

    if ptype in ("shaft", "plug") or "пробк" in str(name).lower():
        lines.append("body_style=cylindrical_steps")
        lines.append("forbid=rectangle_as_main_body")
    if ptype == "bushing":
        lines.append("втулка")

    if feat_types:
        lines.append("required_features=" + ",".join(feat_types))

    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("НЕИЗВЕСТНЫЕ: " + ", ".join(str(u) for u in unk))
    return "\n".join(lines)
