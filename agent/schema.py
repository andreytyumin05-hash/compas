"""Drawing schema and user-facing formatting."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

FEATURE_SCHEMA_TEXT = """
{
  "part_type": "bushing|flange|plate|shaft|cover|bracket|plug|other",
  "name": "string",
  "units": "mm",
  "axis": "Z|X|Y",
  "overall": {
    "width": null, "height": null, "length": null,
    "outer_diameter": null, "inner_diameter": null,
    "thickness": null, "total_height": null
  },
  "drawing": {
    "views": ["main|top|side|section"],
    "solid_lines": "visible solid contour",
    "dashed_lines": "hidden geometry; never an outer contour",
    "centerlines": "axes, symmetry, PCD references",
    "notes": "drawing interpretation notes"
  },
  "build_plan": [
    {
      "id": "S01",
      "type": "extrude_body|boss|step|hole|pattern_holes|pocket|hex_pocket|groove|counterbore|countersink|slot|keyway|chamfer|fillet|revolve",
      "params": {},
      "depends_on": "S00"
    }
  ],
  "features": [
    {
      "id": "F01",
      "type": "extrude_body|boss|step|hole|pattern_holes|pocket|hex_pocket|groove|counterbore|countersink|chamfer|fillet|slot|keyway|revolve",
      "params": {
        "diameter": null, "length": null, "width": null, "height": null,
        "depth": null, "thickness": null, "pcd": null, "count": null,
        "x": null, "y": null, "shape": null, "through_all": null,
        "pilot_diameter": null, "counterbore_diameter": null,
        "counterbore_depth": null, "outer_diameter": null,
        "inner_diameter": null, "fillet_radius": null,
        "chamfer_distance": null, "angle_deg": null,
        "pattern": "circular|linear|points|none"
      },
      "depends_on": "F00",
      "notes": "short engineering note"
    }
  ],
  "patterns_hint": ["N x Ød on PCD ..."],
  "unknown_dimensions": [],
  "warnings": []
}
""".strip()

_TYPE_RU = {
    "bushing": "втулка", "flange": "фланец", "plate": "плита", "shaft": "вал",
    "cover": "крышка", "bracket": "кронштейн", "plug": "пробка", "other": "деталь",
}
_FEAT_RU = {
    "extrude_body": "основное тело", "boss": "бобышка", "step": "ступень",
    "hole": "отверстие", "pattern_holes": "массив отверстий", "pocket": "карман",
    "hex_pocket": "шестигранное углубление", "groove": "канавка",
    "counterbore": "цековка", "countersink": "зенковка", "fillet": "скругление",
    "chamfer": "фаска", "slot": "паз", "keyway": "шпоночный паз", "revolve": "вращение",
}


def _num(v: Any) -> Optional[str]:
    if v is None:
        return None
    try:
        f = float(v)
        return str(int(f)) if f.is_integer() else f"{f:g}"
    except Exception:
        return str(v)


def _flatten_params(params: Any) -> Dict[str, Any]:
    if not isinstance(params, dict):
        return {}
    out: Dict[str, Any] = {}
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (int, float, str, bool)):
            out[str(key)] = value
    return out


def _feat_human(feat: Dict[str, Any]) -> str:
    title = _FEAT_RU.get(str(feat.get("type") or ""), str(feat.get("type") or "элемент"))
    p = _flatten_params(feat.get("params"))
    bits: List[str] = []
    for key, label in (("diameter", "Ø"), ("length", "длина"), ("width", "ширина"),
                       ("height", "высота"), ("depth", "глубина"), ("pcd", "PCD"),
                       ("count", "N"), ("chamfer_distance", "фаска"),
                       ("fillet_radius", "R"), ("thickness", "толщина")):
        if key in p:
            value = _num(p[key])
            if label in {"Ø", "PCD", "N", "R"}:
                bits.append(f"{label}{value}" if label == "Ø" else f"{label} {value}")
            else:
                bits.append(f"{label} {value} мм")
    if p.get("through_all") in (True, "true", "1"):
        bits.append("сквозное")
    if p.get("pattern") and str(p["pattern"]) != "none":
        bits.append(f"массив {p['pattern']}")
    note = str(feat.get("notes") or "").strip()
    if note:
        bits.append(note[:90])
    return f"• {title}: " + ", ".join(bits) if bits else f"• {title}"


def format_spec_for_user(spec: Dict[str, Any]) -> str:
    units = spec.get("units") or "мм"
    ptype = str(spec.get("part_type") or "other")
    name = spec.get("name") or _TYPE_RU.get(ptype, "деталь")
    lines: List[str] = ["Распознал так:", "", f"Деталь: {name} ({_TYPE_RU.get(ptype, ptype)})"]
    if spec.get("axis"):
        lines.append(f"Ось: {spec['axis']}")

    overall = spec.get("overall") or {}
    dims: List[str] = []
    for key, label in (("length", "длина"), ("width", "ширина"), ("height", "высота"),
                       ("thickness", "толщина"), ("total_height", "общая высота"),
                       ("outer_diameter", "Ø нар."), ("inner_diameter", "Ø вн.")):
        if overall.get(key) is not None:
            dims.append(f"{label} {_num(overall[key])} {units}")
    if dims:
        lines.append("Размеры: " + "; ".join(dims))

    plan = spec.get("build_plan") or []
    if plan:
        lines.extend(["", "План построения:"])
        for step in plan[:16]:
            if isinstance(step, dict):
                sid = step.get("id") or "S?"
                stype = step.get("type") or "feature"
                params = _flatten_params(step.get("params"))
                summary = ", ".join(f"{k}={_num(v) if isinstance(v, (int, float)) else v}" for k, v in params.items())
                lines.append(f"  {sid}: {stype}" + (f" ({summary})" if summary else ""))
            elif str(step).strip():
                lines.append(f"  {str(step).strip()}")
    elif spec.get("features"):
        lines.extend(["", "Элементы:"])
        lines.extend(_feat_human(f) for f in spec["features"][:16])

    drawing = spec.get("drawing") or {}
    if drawing.get("dashed_lines") or drawing.get("centerlines") or drawing.get("notes"):
        lines.extend(["", "Чертёж: пунктир/оси не являются наружным контуром."])
        note = drawing.get("notes") or drawing.get("dashed_lines") or drawing.get("centerlines")
        if note:
            lines.append(str(note)[:180])

    if spec.get("patterns_hint"):
        lines.append("Массивы: " + "; ".join(str(x)[:100] for x in spec["patterns_hint"][:4]))
    if spec.get("unknown_dimensions"):
        lines.append("Не прочитано: " + ", ".join(str(x) for x in spec["unknown_dimensions"][:8]))
    if spec.get("warnings"):
        for warning in spec["warnings"][:3]:
            lines.append(f"⚠ {str(warning)[:160]}")
    lines.extend(["", "Если всё верно — «Строить». Иначе укажите исправление размерами текстом."])
    return "\n".join(lines)


def spec_to_task_text(spec: Dict[str, Any]) -> str:
    """Compatibility wrapper; the canonical contract is now shared with codegen."""
    from .contract import spec_to_contract_text
    return spec_to_contract_text(spec)
