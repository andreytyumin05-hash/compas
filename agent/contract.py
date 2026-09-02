"""CAD contract: semantic validation of vision/spec JSON."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def validate_contract(spec: Dict[str, Any]) -> Tuple[bool, List[str]]:
    issues: List[str] = []
    if not isinstance(spec, dict):
        return False, ["contract не dict"]

    overall = spec.get("overall") or {}
    if not isinstance(overall, dict):
        overall = {}

    def _f(key: str):
        v = overall.get(key)
        if v is None:
            return None
        try:
            return float(v)
        except Exception:
            issues.append(f"overall.{key} не число: {v!r}")
            return None

    outer = _f("outer_diameter")
    inner = _f("inner_diameter")
    if outer is not None and inner is not None and inner >= outer:
        issues.append(
            f"inner_diameter ({inner}) должен быть < outer_diameter ({outer})"
        )

    for k in ("thickness", "length", "width", "height", "total_height"):
        v = _f(k)
        if v is not None and v <= 0:
            issues.append(f"overall.{k} должен быть > 0")

    features = spec.get("features") or []
    if not isinstance(features, list):
        issues.append("features должен быть list")
        features = []

    for i, feat in enumerate(features):
        if not isinstance(feat, dict):
            issues.append(f"features[{i}] не object")
            continue
        ftype = str(feat.get("type") or "")
        params = feat.get("params") or {}
        if not isinstance(params, dict):
            params = {}

        def pf(name: str, _p=params, _i=i):
            v = _p.get(name)
            if v is None:
                return None
            try:
                return float(v)
            except Exception:
                issues.append(f"feature[{_i}].{name} не число")
                return None

        d = pf("diameter")
        if d is not None and d <= 0:
            issues.append(f"feature[{i}] diameter должен быть > 0")

        depth = pf("depth")
        if depth is not None and depth < 0:
            issues.append(f"feature[{i}] depth не может быть < 0")

        count = params.get("count")
        if count is not None:
            try:
                if int(count) < 1:
                    issues.append(f"feature[{i}] count должен быть >= 1")
            except Exception:
                issues.append(f"feature[{i}] count не int")

        pcd = pf("pcd")
        if pcd is not None and d is not None and pcd <= d:
            issues.append(f"feature[{i}] PCD ({pcd}) должен быть > diameter ({d})")

        if ftype == "counterbore":
            pilot = pf("pilot_diameter")
            cb = pf("counterbore_diameter")
            if pilot is not None and cb is not None and cb <= pilot:
                issues.append(f"feature[{i}] counterbore_diameter > pilot")

        if ftype in ("groove", "ring_groove"):
            od = pf("outer_diameter")
            id_ = pf("inner_diameter")
            if od is not None and id_ is not None and id_ >= od:
                issues.append(f"feature[{i}] groove: inner < outer")

        dep = feat.get("depends_on")
        if isinstance(dep, int) and dep >= i:
            issues.append(f"feature[{i}] depends_on index={dep} некорректна")

    types = [str(f.get("type") or "") for f in features if isinstance(f, dict)]
    body_idx = next(
        (i for i, t in enumerate(types) if t in ("extrude_body", "boss", "step")),
        None,
    )
    hole_idx = next(
        (
            i
            for i, t in enumerate(types)
            if t in ("hole", "pattern_holes", "pocket", "counterbore")
        ),
        None,
    )
    if body_idx is not None and hole_idx is not None and hole_idx < body_idx:
        issues.append("отверстие/карман раньше тела в features")

    return (len(issues) == 0, list(dict.fromkeys(issues)))
