"""Canonical contract between language/vision planning and CAD code generation."""

from __future__ import annotations

import math
from copy import deepcopy
from typing import Any, Dict, List, Mapping


KNOWN_FEATURES = {
    "extrude_body", "boss", "step", "hole", "pattern_holes", "pocket",
    "hex_pocket", "groove", "counterbore", "countersink", "chamfer",
    "fillet", "slot", "keyway", "revolve", "spline_profile",
}

POSITIVE_KEYS = {
    "diameter", "length", "width", "height", "depth", "thickness", "pcd", "radius",
    "fillet_radius", "chamfer_distance", "pilot_diameter", "counterbore_diameter",
    "counterbore_depth", "inner_diameter", "outer_diameter", "pitch", "count",
}

ALIASES = {
    "circular_pattern": "pattern_holes", "hole_pattern": "pattern_holes",
    "recess": "pocket", "threaded_hole": "hole", "thread": "hole",
    "chamfer_edge": "chamfer", "fillet_edge": "fillet",
    "spline": "spline_profile", "bezier": "spline_profile",
    "blade_profile": "spline_profile", "airfoil": "spline_profile",
}


def _num(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    try:
        number = float(value)
    except (TypeError, ValueError):
        return value
    if not math.isfinite(number):
        return None
    return int(number) if number.is_integer() else number


def _clean_params(params: Any) -> Dict[str, Any]:
    if not isinstance(params, Mapping):
        return {}
    out: Dict[str, Any] = {}
    for raw_key, raw_value in params.items():
        key = str(raw_key).strip()
        if raw_value is None:
            continue
        if key == "count":
            value = _num(raw_value)
            if not isinstance(value, int) or value < 1:
                continue
        elif key in POSITIVE_KEYS:
            value = _num(raw_value)
            if isinstance(value, (int, float)) and value <= 0:
                continue
        elif key in {"x", "y", "z", "angle_deg", "start_angle_deg"}:
            value = _num(raw_value)
        else:
            value = raw_value
        out[key] = value
    return out


def _clean_feature(item: Any, index: int) -> Dict[str, Any] | None:
    if not isinstance(item, Mapping):
        return None
    raw_type = str(item.get("type") or "").strip().lower()
    ftype = ALIASES.get(raw_type, raw_type)
    if ftype not in KNOWN_FEATURES:
        return None
    result: Dict[str, Any] = {
        "id": str(item.get("id") or f"F{index:02d}"),
        "type": ftype,
        "params": _clean_params(item.get("params")),
    }
    for key in ("depends_on", "sketch", "body", "parameter_group"):
        if item.get(key):
            result[key] = str(item[key]).strip()
    if item.get("notes"):
        result["notes"] = str(item["notes"]).strip()[:300]
    return result


def _clean_plan(plan: Any, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    result: List[Dict[str, Any]] = []
    if isinstance(plan, list):
        for index, item in enumerate(plan, 1):
            if isinstance(item, Mapping):
                p = deepcopy(dict(item))
                p["id"] = str(p.get("id") or f"S{index:02d}")
                raw_type = str(p.get("type") or "").strip().lower()
                p["type"] = ALIASES.get(raw_type, raw_type)
                p["params"] = _clean_params(p.get("params"))
                if p.get("depends_on"):
                    p["depends_on"] = str(p["depends_on"]).strip()
                result.append(p)
            elif str(item).strip():
                result.append({"id": f"S{index:02d}", "description": str(item).strip()[:500]})
    if not result:
        for index, feature in enumerate(features, 1):
            result.append({
                "id": f"S{index:02d}",
                "type": feature["type"],
                "params": dict(feature.get("params") or {}),
                **({"depends_on": feature["depends_on"]} if feature.get("depends_on") else {}),
            })
    return result[:48]


def _features_from_plan(plan: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    features: List[Dict[str, Any]] = []
    for index, step in enumerate(plan, 1):
        raw_type = str(step.get("type") or "").strip().lower()
        ftype = ALIASES.get(raw_type, raw_type)
        if ftype not in KNOWN_FEATURES:
            continue
        features.append({
            "id": f"F{index:02d}",
            "type": ftype,
            "params": dict(step.get("params") or {}),
            **({"depends_on": step["depends_on"]} if step.get("depends_on") else {}),
        })
    return features


def _clean_named_parameters(value: Any) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    out: Dict[str, Any] = {}
    for raw_name, raw_value in value.items():
        name = str(raw_name).strip()
        if not name or not name.replace("_", "a").isalnum() or name[0].isdigit():
            continue
        if isinstance(raw_value, Mapping):
            item: Dict[str, Any] = {}
            if "value" in raw_value:
                v = _num(raw_value["value"])
                if v is not None:
                    item["value"] = v
            if raw_value.get("expr"):
                item["expr"] = str(raw_value["expr"]).strip()[:200]
            if raw_value.get("note"):
                item["note"] = str(raw_value["note"]).strip()[:200]
            if item:
                out[name] = item
        else:
            v = _num(raw_value)
            if v is not None:
                out[name] = {"value": v}
    return out


def _clean_relations(value: Any) -> List[Dict[str, str]]:
    if not isinstance(value, list):
        return []
    out: List[Dict[str, str]] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        left = str(item.get("left") or item.get("parameter") or "").strip()
        expr = str(item.get("expr") or item.get("right") or "").strip()
        if left and expr:
            out.append({"left": left, "expr": expr[:200]})
    return out[:64]


def normalize_spec(spec: Any) -> Dict[str, Any]:
    """Normalize legacy/new text/vision JSON into one stable CAD contract."""
    if not isinstance(spec, Mapping):
        raise ValueError("Vision spec must be an object")

    out: Dict[str, Any] = {
        "part_type": str(spec.get("part_type") or "other").strip().lower(),
        "name": str(spec.get("name") or "Деталь").strip()[:120],
        "units": str(spec.get("units") or "mm").strip().lower(),
        "axis": str(spec.get("axis") or "Z").strip().upper(),
        "overall": {},
        "parameters": _clean_named_parameters(spec.get("parameters") or spec.get("params")),
        "relations": _clean_relations(spec.get("relations") or spec.get("parameter_relations")),
        "drawing": {},
        "features": [],
        "build_plan": [],
        "patterns_hint": [str(x).strip()[:180] for x in (spec.get("patterns_hint") or []) if str(x).strip()][:12],
        "unknown_dimensions": [str(x).strip()[:180] for x in (spec.get("unknown_dimensions") or []) if str(x).strip()][:20],
        "warnings": [str(x).strip()[:240] for x in (spec.get("warnings") or []) if str(x).strip()][:20],
    }

    overall = spec.get("overall") or {}
    out["overall"] = {str(k): _num(v) for k, v in overall.items() if v is not None and _num(v) is not None}

    drawing = spec.get("drawing") or {}
    for key in ("views", "solid_lines", "dashed_lines", "centerlines", "notes"):
        if drawing.get(key):
            out["drawing"][key] = drawing[key]

    features: List[Dict[str, Any]] = []
    for index, item in enumerate(spec.get("features") or [], 1):
        cleaned = _clean_feature(item, index)
        if cleaned:
            features.append(cleaned)
    out["features"] = features
    out["build_plan"] = _clean_plan(spec.get("build_plan"), features)
    if not out["features"]:
        out["features"] = _features_from_plan(out["build_plan"])
    if not out["build_plan"]:
        out["build_plan"] = _clean_plan([], out["features"])

    ptype = out["part_type"]
    if ptype not in {"bushing", "flange", "plate", "shaft", "cover", "bracket", "plug", "blade", "fitting", "other"}:
        out["warnings"].append(f"unknown part_type={ptype!r}; using other")
        out["part_type"] = "other"
    if out["units"] not in {"mm", "мм"}:
        out["warnings"].append(f"unsupported units={out['units']!r}; interpreting numeric dimensions as mm")
        out["units"] = "mm"
    if out["axis"] not in {"X", "Y", "Z"}:
        out["axis"] = "Z"
    return out


def _fmt_value(value: Any) -> str:
    return f"{value:g}" if isinstance(value, float) else str(value)


def spec_to_contract_text(spec: Mapping[str, Any]) -> str:
    s = normalize_spec(spec)
    lines = [
        "CAD_CONTRACT v3",
        f"part_type={s['part_type']}", f"name={s['name']}", f"units={s['units']}", f"axis={s['axis']}",
        "RULE: solid_lines=body; dashed/hidden/centerlines are not outer solid geometry",
        "RULE: preserve every measured feature; do not invent missing dimensions",
        "RULE: important dimensions should be named parameters; derived positions should use parameter expressions",
        "",
        "PARAMETERS:",
    ]
    for name, item in s["parameters"].items():
        if isinstance(item, Mapping):
            chunks = []
            if "value" in item:
                chunks.append(f"value={_fmt_value(item['value'])}")
            if item.get("expr"):
                chunks.append(f"expr={item['expr']}")
            if item.get("note"):
                chunks.append(f"note={item['note']}")
            lines.append(f"{name}: " + ", ".join(chunks))
    if not s["parameters"]:
        lines.append("(none explicitly named; generator should create names for critical dimensions)")

    if s["relations"]:
        lines.append("PARAMETER_RELATIONS:")
        for rel in s["relations"]:
            lines.append(f"{rel['left']} = {rel['expr']}")

    lines.extend(["", "OVERALL:"])
    lines += [f"{key}={_fmt_value(value)}" for key, value in s["overall"].items()]
    lines.append("BUILD_PLAN:")
    for step in s["build_plan"]:
        sid = step.get("id") or "S?"
        stype = step.get("type")
        dep = step.get("depends_on")
        desc = step.get("description")
        if stype:
            params = ", ".join(f"{k}={_fmt_value(v)}" for k, v in (step.get("params") or {}).items())
            line = f"{sid}: type={stype}" + (f" | {params}" if params else "")
        else:
            line = f"{sid}: {desc or 'follow feature contract'}"
        if dep:
            line += f" | depends_on={dep}"
        lines.append(line)
    lines.append("FEATURES:")
    for feature in s["features"]:
        params = ", ".join(f"{k}={_fmt_value(v)}" for k, v in feature["params"].items())
        line = f"{feature['id']}: feature={feature['type']}" + (f" | {params}" if params else "")
        if feature.get("depends_on"):
            line += f" | depends_on={feature['depends_on']}"
        if feature.get("sketch"):
            line += f" | sketch={feature['sketch']}"
        if feature.get("parameter_group"):
            line += f" | parameter_group={feature['parameter_group']}"
        if feature.get("notes"):
            line += f" | note={feature['notes']}"
        lines.append(line)
    lines += [f"pattern_hint={x}" for x in s["patterns_hint"]]
    if s["unknown_dimensions"]:
        lines.append("UNKNOWN_DIMENSIONS=" + "; ".join(s["unknown_dimensions"]))
    if s["warnings"]:
        lines.append("VISION_WARNINGS=" + "; ".join(s["warnings"]))
    if s["part_type"] in {"shaft", "plug", "fitting"}:
        lines += ["body_style=cylindrical_steps", "forbid=rectangle_as_main_body"]
    if s["part_type"] == "blade":
        lines += [
            "body_style=curved_profile",
            "prefer=spline_profile",
            "forbid=polyline_as_spline_substitute",
        ]
    return "\n".join(lines)


def contract_feature_types(spec: Mapping[str, Any]) -> List[str]:
    return list(dict.fromkeys(f["type"] for f in normalize_spec(spec)["features"]))
