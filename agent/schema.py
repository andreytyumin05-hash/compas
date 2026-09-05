"""Drawing schema and user-facing formatting."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

FEATURE_SCHEMA_TEXT = """
{
  "part_type": "bushing|flange|plate|shaft|cover|bracket|plug|other",
  "name": "string",
  "units": "mm",
  "axis": "Z|X|Y",
  "overall": {},
  "features": [],
  "build_plan": [],
  "construction": {"feature_order": [], "planes_used": []}
}
""".strip()

_TYPE_RU = {
    "bushing": "втулка", "flange": "фланец", "plate": "плита", "shaft": "вал",
    "cover": "крышка", "bracket": "кронштейн", "plug": "пробка", "other": "деталь",
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


def format_spec_for_user(spec: Dict[str, Any]) -> str:
    ptype = str(spec.get("part_type") or "other")
    name = spec.get("name") or _TYPE_RU.get(ptype, "деталь")
    lines: List[str] = ["Распознал так:", "", f"Деталь: {name}"]
    overall = spec.get("overall") or {}
    dims = []
    for key, label in (("length", "длина"), ("width", "ширина"), ("thickness", "толщина"),
                       ("outer_diameter", "Ø нар."), ("inner_diameter", "Ø вн.")):
        if overall.get(key) is not None:
            dims.append(f"{label} {_num(overall[key])}")
    if dims:
        lines.append("Размеры: " + "; ".join(dims))
    return "\n".join(lines)


def spec_to_task_text(spec: Dict[str, Any]) -> str:
    """Contract text + construction feature_order/planes for codegen/tests."""
    from .contract import spec_to_contract_text

    text = spec_to_contract_text(spec)
    # aliases expected by offline tests
    text = re.sub(
        r"(feature=fillet[^
]*radius=([0-9.]+))",
        r"\1, fillet_radius=\2",
        text,
    )
    text = re.sub(
        r"(feature=pocket[^
]*depth=([0-9.]+))",
        r"\1, pocket_depth=\2",
        text,
    )

    construction = (spec or {}).get("construction") or {}
    extra: List[str] = []
    if isinstance(construction, dict):
        fo = construction.get("feature_order") or []
        if isinstance(fo, list) and fo:
            extra.append("feature_order=" + "->".join(str(x) for x in fo))
        for pl in construction.get("planes_used") or construction.get("planes") or []:
            extra.append(f"plane={pl}")
        if construction.get("notes"):
            extra.append(f"construction_notes={construction.get('notes')}")

    if extra:
        if "\nOVERALL:" in text:
            head, tail = text.split("\nOVERALL:", 1)
            text = head + "\n" + "\n".join(extra) + "\nOVERALL:" + tail
        else:
            text = text + "\n" + "\n".join(extra)
    return text
