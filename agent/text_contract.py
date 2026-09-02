"""Текст → структурированный contract (без vision)."""

from __future__ import annotations

import re
from typing import Any, Dict, List


def parse_technical_text(task: str) -> Dict[str, Any]:
    t = (task or "").strip()
    low = t.lower()
    features: List[Dict[str, Any]] = []
    params: Dict[str, Any] = {}
    warnings: List[str] = []

    steps = re.findall(
        r"(?:ø|∅)\s*(\d+(?:[.,]\d+)?)\s*(?:длиной|длина|l\s*)\s*(\d+(?:[.,]\d+)?)",
        low,
    )
    for i, (d, L) in enumerate(steps):
        features.append(
            {
                "type": "step" if i else "extrude_body",
                "params": {"diameter": float(d.replace(",", ".")), "length": float(L.replace(",", "."))},
                "notes": f"ступень {i+1}",
            }
        )
        params[f"D{i+1}"] = float(d.replace(",", "."))
        params[f"L{i+1}"] = float(L.replace(",", "."))

    m = re.search(r"сквозн\w*\s+отверст\w*\s*(?:ø|∅)?\s*(\d+(?:[.,]\d+)?)", low)
    if m:
        d = float(m.group(1).replace(",", "."))
        features.append({"type": "hole", "params": {"diameter": d, "through_all": True}})
        params["D_inner"] = d

    if "канавк" in low:
        m = re.search(r"канавк\w*.*?(\d+(?:[.,]\d+)?)", low)
        w = float(m.group(1).replace(",", ".")) if m else 4.0
        features.append({"type": "groove", "params": {"width": w}})
        params["GROOVE_W"] = w

    m = re.search(r"фаск[аи]\s*(\d+(?:[.,]\d+)?)\s*[xх×]\s*(\d+)", low)
    if m or "фаск" in low:
        dist = float(m.group(1).replace(",", ".")) if m else 2.0
        features.append({"type": "chamfer", "params": {"distance": dist}})
        params["CHAMFER"] = dist

    part_type = "other"
    if "штуцер" in low:
        part_type = "fitting"
    elif "втулк" in low:
        part_type = "bushing"
    elif "вал" in low:
        part_type = "shaft"
    elif "лопаст" in low:
        part_type = "blade"

    build_plan = [f"{i+1}. {f['type']}: {f.get('params')}" for i, f in enumerate(features)]
    return {
        "part_type": part_type,
        "source": "text",
        "params": params,
        "features": features,
        "build_plan": build_plan,
        "warnings": warnings,
        "raw": t[:500],
    }


def contract_to_codegen_hints(contract: Dict[str, Any]) -> str:
    lines = ["## CONTRACT (из текста, не выдумывай размеры)"]
    params = contract.get("params") or {}
    if params:
        lines.append("PARAMETERS:")
        for k, v in params.items():
            lines.append(f"  {k} = {v}")
    for p in contract.get("build_plan") or []:
        lines.append(f"  {p}")
    lines.append(
        "part.param('NAME', value); геометрия через part.p('NAME'). "
        "Ступени = отдельные sketch+extrude. spline только для кривых профилей."
    )
    return "\n".join(lines)
