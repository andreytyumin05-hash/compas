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
    "outer_diameter": null, "inner_diameter": null, "thickness": null,
    "total_height": null
  },
  "construction": {
    "feature_order": ["base", "boss", "pocket", "pattern_holes", "fillet", "chamfer", "slot"],
    "planes_used": ["xy", "xz", "yz"],
    "notes": "строка"
  },
  "features": [
    {
      "type": "extrude_body|boss|hole|pocket|chamfer|fillet|slot|pattern_holes|step|recess|rib",
      "params": {
        "shape": "stadium|rect|circle|slot|ellipse",
        "length": null, "width": null, "thickness": null,
        "outer_radius": null, "corner_radius": null,
        "boss_height": null, "radius": null, "diameter": null,
        "depth": null, "pocket_depth": null, "pcd": null, "count": null,
        "x": null, "y": null, "z": null, "plane": null,
        "step_height": null, "step_width": null, "fillet_radius": null,
        "chamfer_distance": null, "slot_width": null
      },
      "confidence": 0.0,
      "notes": ""
    }
  ],
  "unknown_dimensions": [],
  "warnings": [],
  "quality": {
    "view_coverage": "front|top|side|multi-view",
    "is_symmetrical": true,
    "has_holes": false,
    "has_pocket": false,
    "has_step": false,
    "has_fillets": false,
    "has_chamfers": false
  }
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
    Добавляет порядок построения, плоскости и типы фич, чтобы сложная модель
    попадала в понятный для вторичной модели машинный текст.
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
        "total_height",
    ):
        v = overall.get(k)
        if v is not None:
            lines.append(f"{k}={v}")

    construction = spec.get("construction") or {}
    feature_order = construction.get("feature_order") or []
    if feature_order:
        order = "->".join(str(x) for x in feature_order)
        lines.append(f"feature_order={order}")
    planes = construction.get("planes_used") or []
    for plane in planes:
        if plane:
            lines.append(f"plane={plane}")
    notes = construction.get("notes")
    if notes:
        lines.append(str(notes))

    # агрегаты из features
    for feat in spec.get("features") or []:
        ftype = str(feat.get("type") or "")
        p = _flatten_params(feat.get("params"))
        if ftype in ("extrude_body", "boss", "step", "rib") or p.get("shape") in (
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
                "step_height",
                "step_width",
            ):
                if key in p and p[key] is not None:
                    lines.append(f"{key}={p[key]}")
            if p.get("shape"):
                lines.append(f"shape={p['shape']}")
        if ftype in ("hole", "pocket", "recess", "step") or "diameter" in p or "depth" in p:
            if "diameter" in p:
                lines.append(f"hole_diameter={p['diameter']}")
            if "depth" in p:
                lines.append(f"pocket_depth={p['depth']}")
            if "pocket_depth" in p:
                lines.append(f"pocket_depth={p['pocket_depth']}")
            if "x" in p and "y" in p:
                lines.append(f"hole_x={p['x']} hole_y={p['y']}")
            if "plane" in p:
                lines.append(f"plane={p['plane']}")
        if ftype == "pattern_holes":
            if "pcd" in p:
                lines.append(f"pcd={p['pcd']}")
            if "count" in p:
                lines.append(f"hole_count={p['count']}")
            if "diameter" in p:
                lines.append(f"hole_diameter={p['diameter']}")
        if ftype == "fillet" and "radius" in p:
            lines.append(f"fillet_radius={p['radius']}")
        if ftype == "chamfer" and "distance" in p:
            lines.append(f"chamfer_distance={p['distance']}")
        if ftype == "slot" and "slot_width" in p:
            lines.append(f"slot_width={p['slot_width']}")
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
