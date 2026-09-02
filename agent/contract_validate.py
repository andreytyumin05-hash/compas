"""Semantic validation for the canonical vision-to-CAD contract.

The validator is intentionally conservative: impossible relationships are hard
errors; unreadable or missing dimensions remain warnings so the VLM does not
invent geometry just to satisfy a schema.
"""

from __future__ import annotations

from typing import Any, Dict, List, Mapping, Tuple


_RELATIONS = (
    ("inner_diameter", "outer_diameter", "inner_diameter must be < outer_diameter"),
    ("pilot_diameter", "counterbore_diameter", "pilot_diameter must be < counterbore_diameter"),
    ("pilot_diameter", "countersink_diameter", "pilot_diameter must be < countersink_diameter"),
)


def _num(params: Mapping[str, Any], key: str) -> float | None:
    value = params.get(key)
    try:
        return float(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def validate_contract(spec: Mapping[str, Any]) -> Tuple[List[str], List[str]]:
    """Return (hard_errors, warnings) without mutating the input contract."""
    errors: List[str] = []
    warnings: List[str] = []
    features = spec.get("features") or []
    plan = spec.get("build_plan") or []

    if not features and not plan:
        errors.append("contract contains neither features nor build_plan")
        return errors, warnings

    feature_ids = set()
    for index, feature in enumerate(features, 1):
        if not isinstance(feature, Mapping):
            errors.append(f"feature[{index}] is not an object")
            continue
        fid = str(feature.get("id") or f"F{index:02d}")
        if fid in feature_ids:
            errors.append(f"duplicate feature id: {fid}")
        feature_ids.add(fid)
        dep = feature.get("depends_on")
        if dep and str(dep) not in feature_ids and str(dep) != "F00":
            warnings.append(f"feature {fid}: dependency {dep!r} is not an earlier feature")

        ftype = str(feature.get("type") or "")
        params = feature.get("params") or {}
        if not isinstance(params, Mapping):
            warnings.append(f"feature {fid}: params is not an object")
            params = {}

        for low, high, message in _RELATIONS:
            a, b = _num(params, low), _num(params, high)
            if a is not None and b is not None and a >= b:
                errors.append(f"feature {fid}: {message}")

        if ftype in {"pattern_holes", "pattern_holes_circular"}:
            count = _num(params, "count")
            pcd = _num(params, "pcd")
            diameter = _num(params, "diameter")
            if count is not None and (count < 1 or int(count) != count):
                errors.append(f"feature {fid}: count must be a positive integer")
            if pcd is not None and pcd <= 0:
                errors.append(f"feature {fid}: pcd must be > 0")
            if diameter is not None and diameter <= 0:
                errors.append(f"feature {fid}: diameter must be > 0")
        elif ftype in {"hole", "counterbore", "countersink"}:
            diameter = _num(params, "diameter")
            if diameter is not None and diameter <= 0:
                errors.append(f"feature {fid}: diameter must be > 0")
        elif ftype in {"extrude_body", "boss", "step"}:
            for key in ("diameter", "length", "width", "height", "depth", "thickness"):
                value = params.get(key)
                if value is None:
                    continue
                try:
                    if float(value) <= 0:
                        errors.append(f"feature {fid}: {key} must be > 0")
                except (TypeError, ValueError):
                    warnings.append(f"feature {fid}: {key} is non-numeric")

    plan_ids = set()
    for index, step in enumerate(plan, 1):
        if not isinstance(step, Mapping):
            warnings.append(f"plan step {index} is free-form text")
            continue
        sid = str(step.get("id") or f"S{index:02d}")
        if sid in plan_ids:
            errors.append(f"duplicate build-plan id: {sid}")
        plan_ids.add(sid)
        dep = step.get("depends_on")
        if dep and str(dep) not in plan_ids and str(dep) != "S00":
            warnings.append(f"plan step {sid}: dependency {dep!r} is not an earlier step")

    unknown = spec.get("unknown_dimensions") or []
    if unknown:
        warnings.append(f"{len(unknown)} unreadable dimension(s) preserved as unknown")

    return list(dict.fromkeys(errors)), list(dict.fromkeys(warnings))
