"""Canonical contract between drawing vision and CAD code generation."""

from __future__ import annotations

import math
import re
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Mapping

KNOWN_FEATURES = {
    "extrude_body", "boss", "step", "hole", "pattern_holes", "pocket",
    "hex_pocket", "groove", "counterbore", "countersink", "chamfer",
    "fillet", "slot", "keyway", "revolve",
}

POSITIVE_KEYS = {
    "diameter", "length", "width", "height", "depth", "thickness",
    "pcd", "count", "radius", "fillet_radius", "chamfer_distance",
    "pilot_diameter", "counterbore_diameter", "counterbore_depth",
    "inner_diameter", "outer_diameter", "pitch",
}

ALIASES = {
    "circular_pattern": "pattern_holes",
    "hole_pattern": "pattern_holes",
    "recess": "pocket",
    "threaded_hole": "hole",
    "thread": "hole",
    "chamfer_edge": "chamfer",
    "fillet_edge": "fillet",
}


def _num(value: Any) -> Any:
    if value is None or isinstance(value, bool):
        return value
    try:
        f = float(value)
    except (TypeError, ValueError):
        return value
    if not math.isfinite(f):
        return None
    return int(f) if f.is_integer() else f


def _clean_params(params: Any) -> Dict[str, Any]:
    if not isinstance(params, Mapping):
        return {}
    out: Dict[str, Any] = {}
    for key, value in params.items():
        key = str(key).strip()
        if value is None:
            continue
        if key in POSITIVE_KEYS:
            value = _num(value)
            if isinstance(value, (int, float)) and value <= 0:
                continue
        elif key in {"x", "y", "angle_deg", "start_angle_deg"}:
            value = _num(value)
        elif key == "count":
            value = _num(value)
            if isinstance(value, int) and value < 1:
                continue
        out[key] = value
    return out


def _clean_feature(item: Any, index: int) -> Dict[str, Any] | None:
    if not isinstance(item, Mapping):
        return None
    raw_type = str(item.get("type") or "").strip().lower()
    ftype = ALIASES.get(raw_type, raw_type)
    if ftype not in KNOWN_FEATURES:
        return None
    params = _clean_params(item.get("params"))
    result: Dict[str, Any] = {
        "id": str(item.get("id") or f"F{index:02d}"),
        "type": ftype,
        "params": params,
    }
    dep = item.get("depends_on")
    if dep:
        result["depends_on"] = str(dep).strip()
    note = item.get("notes")
    if note:
        result["notes"] = str(note).strip()[:300]
    return result


def _clean_plan(plan: Any, features: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(plan, list):
        plan = []
    result: List[Dict[str, Any]] = []
    for index, item in enumerate(plan, 1):
        if isinstance(item, Mapping):
            p = deepcopy(dict(item))
            p["id"] = str(p.get("id") or f"S{index:02d}")
            p["type"] = ALIASES.get(str(p.get("type") or "").lower(), str(p.get("type") or "").lower())
            p["params"] = _clean_params(p.get("params"))
            dep = p.get("depends_on")
            if dep:
                p["depends_on"] = str(dep)
            result.append(p)
        elif str(item).strip():
            result.append({"id": f"S{index:02d}", "description": str(item).strip()[:500]})
    if not result:
        for index, feature in enumerate(features, 1):
            result.append({
                "id": f"S{index:02d}",
                "type": feature["type"],
                "params": dict(feature.get("params") or {}),
                "depends_on": feature.get("depends_on"),
            })
    return result[:32]


def normalize_spec(spec: Any) -> Dict[str, Any]:
    """Normalize legacy/new vision JSON into one stable, LLM-friendly shape."""
    if not isinstance(spec, Mapping):
        raise ValueError("Vision spec must be an object")

    out: Dict[str, Any] = {
        "part_type": str(spec.get("part_type") or "other").strip().lower(),
        "name": str(spec.get("name") or "Деталь").strip()[:120],
        "units": str(spec.get("units") or "mm").strip().lower(),
        "axis": str(spec.get("axis") or "Z").strip().upper(),
        "overall": {},
        "drawing": {},
        "features": [],
        "patterns_hint": [str(x).strip()[:180] for x in (spec.get("patterns_hint") or []) if str(x).strip()][:12],
        "unknown_dimensions": [str(x).strip()[:180] for x in (spec.get("unknown_dimensions") or []) if str(x).strip()][:20],
        "warnings": [str(x).strip()[:240] for x in (spec.get("warnings") or []) if str(x).strip()][:20],
    }
    out["overall"] = {
        str(k): _num(v) for k, v in (spec.get("overall") or {}).items()
        if v is not None and _num(v) is not None
    }
    drawing = spec.get("drawing") or {}
    for key in ("views", "solid_lines", "dashed_lines", "centerlines", "notes"):
        value = drawing.get(key)
        if value:
            out["drawing"][key] = value

    features: List[Dict[str, Any]] = []
    for index, item in enumerate(spec.get("features") or [], 1):
        cleaned = _clean_feature(item, index)
        if cleaned:
            features.append(cleaned)
    out["features"] = features
    out["build_plan"] = _clean_plan(spec.get("build_plan"), features)

    ptype = out["part_type"]
    if ptype not in {"bushing", "flange", "plate", "shaft", "cover", "bracket", "plug", "other"}:
        out["warnings"].append(f"unknown part_type={ptype!r}; using other")
        out["part_type"] = "other"
    if out["units"] not in {"mm", "мм"}:
        out["warnings"].append(f"unsupported units={out['units']!r}; interpreting numeric dimensions as mm")
        out["units"] = "mm"
    if out["axis"] not in {"X", "Y", "Z"}:
        out["axis"] = "Z"
    return out


def _fmt_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:g}"
    return str(value)


def spec_to_contract_text(spec: Mapping[str, Any]) -> str:
    """Serialize spec into deterministic lines; avoids prose-trigger confusion."""
    s = normalize_spec(spec)
    lines = [
        "CAD_CONTRACT v2",
        f"part_type={s['part_type']}",
        f"name={s['name']}",
        f"units={s['units']}",
        f"axis={s['axis']}",
        "RULE: solid_lines=body; dashed/hidden/centerlines are not outer solid geometry",
        "RULE: preserve every measured feature; do not invent missing dimensions",
        "",
        "OVERALL:",
    ]
    for key, value in s["overall"].items():
        lines.append(f"{key}={_fmt_value(value)}")

    lines.append("BUILD_PLAN:")
    for step in s["build_plan"]:
        sid = step.get("id")
        stype = step.get("type")
        dep = step.get("depends_on")
        desc = step.get("description")
        if stype:
            params = ", ".join(f"{k}={_fmt_value(v)}" for k, v in (step.get("params") or {}).items())
            line = f"{sid}: type={stype}"
            if params:
                line += f" | {params}"
        else:
            line = f"{sid}: {desc or 'follow feature contract'}"
        if dep:
            line += f" | depends_on={dep}"
        lines.append(line)

    lines.append("FEATURES:")
    for feature in s["features"]:
        params = ", ".join(f"{k}={_fmt_value(v)}" for k, v in feature["params"].items())
        line = f"{feature['id']}: feature={feature['type']}"
        if params:
            line += f" | {params}"
        if feature.get("depends_on"):
            line += f" | depends_on={feature['depends_on']}"
        if feature.get("notes"):
            line += f" | note={feature['notes']}"
        lines.append(line)

    for hint in s["patterns_hint"]:
        lines.append(f"pattern_hint={hint}")
    if s["unknown_dimensions"]:
        lines.append("UNKNOWN_DIMENSIONS=" + "; ".join(s["unknown_dimensions"]))
    if s["warnings"]:
        lines.append("VISION_WARNINGS=" + "; ".join(s["warnings"]))

    if s["part_type"] in {"shaft", "plug"}:
        lines.append("body_style=cylindrical_steps")
        lines.append("forbid=rectangle_as_main_body")

    return "\n".join(lines)


def contract_feature_types(spec: Mapping[str, Any]) -> List[str]:
    s = normalize_spec(spec)
    return list(dict.fromkeys(f["type"] for f in s["features"]))
