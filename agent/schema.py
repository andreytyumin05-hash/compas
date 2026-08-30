"""JSON-схема чертежа → ТЗ для шаблонов/LLM."""

from __future__ import annotations

from typing import Any, Dict, List

FEATURE_SCHEMA_TEXT = """
{
  "part_type": "bushing|flange|plate|shaft|cover|bracket|other",
  "name": "строка",
  "units": "mm",
  "overall": {
    "width": null, "height": null, "length": null,
    "outer_diameter": null, "inner_diameter": null, "thickness": null
  },
  "features": [
    {
      "type": "extrude_body|boss|hole|pocket|chamfer|fillet|slot|pattern_holes",
      "params": {
        "shape": "stadium|rect|circle",
        "length": null, "width": null, "thickness": null,
        "outer_radius": null, "corner_radius": null,
        "boss_height": null, "radius": null, "diameter": null,
        "pcd": null, "count": null, "x": null, "y": null
      },
      "confidence": 0.0,
      "notes": ""
    }
  ],
  "unknown_dimensions": [],
  "warnings": []
}
""".strip()


def _flatten_params(params: Any) -> Dict[str, Any]:
    if not isinstance(params, dict):
        return {}
    out = {}
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


def spec_to_task_text(spec: Dict[str, Any]) -> str:
    """
    ТЗ с явными key=value — чтобы templates.py ловил без LLM.
    """
    lines: List[str] = []
    ptype = str(spec.get("part_type") or "other")
    name = spec.get("name") or ptype
    lines.append(f"Деталь: {name} (тип {ptype}), единицы: {spec.get('units', 'mm')}")

    overall = spec.get("overall") or {}
    for k in (
        "length",
        "width",
        "height",
        "thickness",
        "outer_diameter",
        "inner_diameter",
    ):
        v = overall.get(k)
        if v is not None:
            lines.append(f"{k}={v}")

    # агрегаты из features
    for feat in spec.get("features") or []:
        ftype = str(feat.get("type") or "")
        p = _flatten_params(feat.get("params"))
        if ftype in ("extrude_body", "boss") or p.get("shape") in (
            "stadium",
            "oblong",
            "rounded",
        ):
            for key in (
                "length",
                "width",
                "thickness",
                "outer_radius",
                "corner_radius",
                "boss_height",
                "radius_outer",
                "inner_radius",
                "radius",
                "total_height",
            ):
                if key in p and p[key] is not None:
                    lines.append(f"{key}={p[key]}")
            if p.get("shape"):
                lines.append(f"shape={p['shape']}")
        if ftype == "hole" or "diameter" in p:
            if "diameter" in p:
                lines.append(f"hole_diameter={p['diameter']}")
            if "x" in p and "y" in p:
                lines.append(f"hole_x={p['x']} hole_y={p['y']}")
        if ftype == "pattern_holes":
            if "pcd" in p:
                lines.append(f"pcd={p['pcd']}")
            if "count" in p:
                lines.append(f"hole_count={p['count']}")
            if "diameter" in p:
                lines.append(f"hole_diameter={p['diameter']}")
        if feat.get("notes"):
            lines.append(str(feat["notes"]))

    # ключевые слова для try_template
    if ptype in ("cover", "flange", "plate") or "stadium" in " ".join(lines).lower():
        lines.append("крышка flange stadium")
    if ptype == "bushing":
        lines.append("втулка")
        od = overall.get("outer_diameter")
        id_ = overall.get("inner_diameter")
        L = overall.get("length") or overall.get("height")
        if od and id_ and L:
            lines.append(f"наружный {od} внутренний {id_} длина {L}")

    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("НЕИЗВЕСТНЫЕ: " + ", ".join(str(u) for u in unk))
    return "\n".join(lines)


def format_spec_for_user(spec: Dict[str, Any]) -> str:
    lines = ["Я понял чертёж так:", ""]
    lines.append(f"• Тип: {spec.get('part_type', '?')}")
    if spec.get("name"):
        lines.append(f"• Имя: {spec['name']}")
    overall = spec.get("overall") or {}
    for k, v in overall.items():
        if v is not None:
            lines.append(f"• {k}: {v} {spec.get('units', 'mm')}")
    for f in spec.get("features") or []:
        lines.append(f"  – {f.get('type')}: {f.get('params')}")
    unk = spec.get("unknown_dimensions") or []
    if unk:
        lines.append("⚠️ Не прочитано: " + ", ".join(str(u) for u in unk))
    lines.append("")
    lines.append("Верно? «да» / кнопки или исправьте размеры текстом.")
    return "\n".join(lines)
