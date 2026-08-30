"""JSON-схема чертежа → ТЗ для агента + понятный текст для пользователя."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

FEATURE_SCHEMA_TEXT = """
{
  "part_type": "bushing|flange|plate|shaft|cover|bracket|other",
  "name": "строка",
  "units": "mm",
  "overall": {
    "width": null, "height": null, "length": null,
    "outer_diameter": null, "inner_diameter": null, "thickness": null,
    "total_height": null
  },
  "features": [
    {
      "type": "extrude_body|boss|hole|pocket|chamfer|fillet|slot|pattern_holes|step",
      "params": { },
      "notes": "кратко по-русски что это"
    }
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
    "other": "деталь",
}

_FEAT_RU = {
    "extrude_body": "основное тело",
    "boss": "бобышка / выступ",
    "step": "ступень / уступ",
    "hole": "отверстие",
    "pocket": "карман (глухой вырез)",
    "recess": "выборки",
    "pattern_holes": "группа отверстий",
    "fillet": "скругление",
    "chamfer": "фаска",
    "slot": "паз",
    "rib": "ребро",
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
                if isinstance(v2, (int, float, str)):
                    out[f"{k}_{k2}"] = v2
    return out


def _feat_human(feat: Dict[str, Any]) -> str:
    """Одна строка для пользователя, без shape= и сырого JSON."""
    ftype = str(feat.get("type") or "")
    title = _FEAT_RU.get(ftype, ftype or "элемент")
    p = _flatten_params(feat.get("params"))
    bits: List[str] = []

    shape = str(p.get("shape") or "").lower()
    if shape in ("stadium", "oblong", "rounded"):
        bits.append("овальный контур")
    elif shape == "rect":
        bits.append("прямоугольник")
    elif shape == "circle":
        bits.append("круг")

    L, W = p.get("length"), p.get("width")
    if L is not None and W is not None:
        bits.append(f"{_num(L)}×{_num(W)} мм")
    elif L is not None:
        bits.append(f"длина {_num(L)} мм")

    for key, label in (
        ("thickness", "толщина"),
        ("boss_height", "высота"),
        ("depth", "глубина"),
        ("pocket_depth", "глубина"),
        ("diameter", "Ø"),
        ("radius", "R"),
        ("outer_radius", "R скругления"),
        ("corner_radius", "R угла"),
        ("step_height", "высота ступени"),
        ("pcd", "диаметр расположения"),
        ("count", "кол-во"),
        ("fillet_radius", "R"),
        ("chamfer_distance", "фаска"),
    ):
        if key in p and p[key] is not None:
            if label == "Ø":
                bits.append(f"Ø{_num(p[key])} мм")
            elif label == "R" or label.startswith("R"):
                bits.append(f"{label}{_num(p[key])} мм")
            else:
                bits.append(f"{label} {_num(p[key])} мм")

    through = p.get("through_all") or p.get("through")
    if through is True or str(through).lower() in ("true", "1", "yes"):
        bits.append("сквозное")
    elif ftype in ("pocket", "hole") and (p.get("depth") or p.get("pocket_depth")):
        bits.append("глухое")

    note = (feat.get("notes") or "").strip()
    if note and len(note) < 80 and "{" not in note:
        bits.append(note)

    if bits:
        return f"• {title}: " + ", ".join(bits)
    return f"• {title}"


def format_spec_for_user(spec: Dict[str, Any]) -> str:
    """Короткое понятное подтверждение в Telegram — без shape/JSON."""
    units = spec.get("units") or "мм"
    ptype = str(spec.get("part_type") or "other")
    name = spec.get("name") or _TYPE_RU.get(ptype, "деталь")

    lines: List[str] = [
        "Распознал так:",
        "",
        f"Деталь: {name} ({_TYPE_RU.get(ptype, ptype)})",
    ]

    overall = spec.get("overall") or {}
    dim_bits = []
    if overall.get("length") is not None and overall.get("width") is not None:
        dim_bits.append(
            f"габарит {_num(overall['length'])}×{_num(overall['width'])} {units}"
        )
    if overall.get("thickness") is not None:
        dim_bits.append(f"толщина {_num(overall['thickness'])} {units}")
    if overall.get("total_height") is not None:
        dim_bits.append(f"общая высота {_num(overall['total_height'])} {units}")
    if overall.get("outer_diameter") is not None:
        dim_bits.append(f"Ø нар. {_num(overall['outer_diameter'])} {units}")
    if overall.get("inner_diameter") is not None:
        dim_bits.append(f"Ø вн. {_num(overall['inner_diameter'])} {units}")
    if dim_bits:
        lines.append("Размеры: " + "; ".join(dim_bits))

    lines.append("")
    lines.append("Буду строить по шагам:")
    feats = spec.get("features") or []
    if not feats:
        lines.append("• одно тело по габаритам выше")
    else:
        for f in feats:
            lines.append(_feat_human(f))

    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("")
        lines.append(
            "Не удалось прочитать: " + ", ".join(str(u) for u in unk[:8])
        )

    for w in (spec.get("warnings") or [])[:3]:
        if w and isinstance(w, str) and len(w) < 120:
            lines.append(f"⚠ {w}")

    lines.append("")
    lines.append("Если верно — «Строить». Если нет — пришлите размеры текстом.")
    return "\n".join(lines)


def spec_to_task_text(spec: Dict[str, Any]) -> str:
    """Машинное ТЗ для templates/LLM (key=value)."""
    lines: List[str] = []
    ptype = str(spec.get("part_type") or "other")
    name = spec.get("name") or ptype
    lines.append(f"Деталь: {name} (тип {ptype})")
    lines.append("Порядок: база → ступени/бобышки → карманы/отверстия → фаски/скругления")

    overall = spec.get("overall") or {}
    for k in (
        "length",
        "width",
        "height",
        "thickness",
        "outer_diameter",
        "inner_diameter",
        "total_height",
    ):
        v = overall.get(k)
        if v is not None:
            lines.append(f"{k}={v}")

    for feat in spec.get("features") or []:
        ftype = str(feat.get("type") or "")
        p = _flatten_params(feat.get("params"))
        lines.append(f"feature={ftype}")
        for key, val in p.items():
            if isinstance(val, (int, float, str)) and str(val):
                lines.append(f"{key}={val}")
        if feat.get("notes"):
            lines.append(str(feat["notes"]))

    if ptype in ("cover", "flange", "plate") or any(
        "stadium" in str(f).lower() for f in lines
    ):
        lines.append("крышка flange stadium")
    if ptype == "bushing":
        lines.append("втулка")
        od, id_, L = (
            overall.get("outer_diameter"),
            overall.get("inner_diameter"),
            overall.get("length") or overall.get("height"),
        )
        if od and id_ and L:
            lines.append(f"наружный {od} внутренний {id_} длина {L}")

    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("НЕИЗВЕСТНЫЕ: " + ", ".join(str(u) for u in unk))
    return "\n".join(lines)
