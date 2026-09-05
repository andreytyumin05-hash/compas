"""Code normalization and deterministic task-coverage checks."""

from __future__ import annotations

import ast
import re
import textwrap
from typing import List, Set


def normalize_code(code: str) -> str:
    value = (code or "").replace("\r\n", "\n").replace("\t", "    ").strip()
    value = re.sub(r"^\s*```(?:python)?\s*", "", value, flags=re.I)
    value = re.sub(r"\s*```\s*$", "", value)
    try:
        ded = textwrap.dedent(value)
        ast.parse(ded)
        return ded.strip() + "\n"
    except SyntaxError:
        return value + ("\n" if value and not value.endswith("\n") else "")


def semantic_warnings(code: str) -> List[str]:
    warnings: List[str] = []
    low = (code or "").lower()
    if (
        "cylindrical_steps" in low
        and low.count("part.extrude(") == 1
        and "part.revolve(" not in low
    ):
        warnings.append("цилиндрическая ступенчатая деталь имеет только одно additive extrude")
    if "dim_" not in low:
        warnings.append("в скрипте нет размерных annotations; редактирование будет менее наглядным")
    return warnings


def _feature_types_from_task(task: str) -> Set[str]:
    found: Set[str] = set()
    for match in re.finditer(r"(?:^|\n)\s*(?:[FS]\w+\s*:\s*)?feature\s*=\s*([a-z_]+)", task or "", flags=re.I):
        found.add(match.group(1).lower())
    for match in re.finditer(r"required_features\s*=\s*([a-z_,\s]+)", task or "", flags=re.I):
        found.update(x.strip().lower() for x in match.group(1).split(",") if x.strip())
    return found


def _method_present(code: str, *names: str) -> bool:
    low = (code or "").lower()
    return any(re.search(rf"\bpart\.{re.escape(name)}\s*\(", low) for name in names)


def check_task_feature_requirements(task: str, code: str) -> List[str]:
    low_t = (task or "").lower()
    low_c = (code or "").lower()
    if not low_t.strip() or not low_c.strip():
        return []

    lines = []
    for line in low_t.splitlines():
        s = line.strip()
        if s.startswith(("rule:", "правило:", "ops_order=", "порядок:")):
            continue
        lines.append(s)
    low_t = "\n".join(lines)

    feats = _feature_types_from_task(task)
    missing: List[str] = []

    def require(ok: bool, label: str) -> None:
        if not ok:
            missing.append(label)

    if feats & {"hole", "pattern_holes"}:
        require(_method_present(low_c, "hole", "pattern_holes_circular", "pattern_holes_linear", "pattern_holes_points", "pattern_holes_rect", "hole_list"), "hole")
    if feats & {"pocket", "hex_pocket"}:
        if feats & {"hex_pocket"}:
            require(_method_present(low_c, "pocket", "cut") and ("polygon(" in low_c or "hex_boss(" in low_c or "hex_pocket" in low_c), "hex_pocket")
        else:
            require(_method_present(low_c, "pocket", "cut"), "pocket")
    if "groove" in feats:
        require(_method_present(low_c, "ring_groove", "groove") or (low_c.count("circle(") >= 2 and "part.cut(" in low_c), "groove")
    if "counterbore" in feats:
        require(_method_present(low_c, "counterbore"), "counterbore")
    if "countersink" in feats:
        require(_method_present(low_c, "countersink"), "countersink")
    if "chamfer" in feats:
        require(_method_present(low_c, "chamfer", "chamfer_edge"), "chamfer")
    if "fillet" in feats:
        require(_method_present(low_c, "fillet", "fillet_edge"), "fillet")
    if feats & {"slot", "keyway"}:
        require(_method_present(low_c, "slot", "keyway"), "slot/keyway")
    if feats & {"boss"}:
        require(_method_present(low_c, "boss", "hex_boss"), "boss")

    turned = "body_style=cylindrical_steps" in low_t or any(
        word in low_t for word in ("пробк", "штуцер", "shaft", "вал", "втулк", "осесимметр")
    )
    if feats & {"step", "extrude_body"}:
        require(_method_present(low_c, "extrude", "step", "boss", "revolve"), "base/additive feature")
    if turned and any(word in low_t for word in ("ступен", "step=")):
        # A single revolve is a preferred and valid representation of all
        # coaxial steps. Do not force multiple independent cylinders.
        n_add = (
            low_c.count("part.extrude(")
            + low_c.count("part.step(")
            + low_c.count("part.boss(")
            + low_c.count("part.hex_boss(")
        )
        if n_add < 2 and "part.revolve(" not in low_c:
            missing.append("multiple additive steps or one revolved profile")
    if turned and not _method_present(low_c, "extrude", "step", "boss", "revolve"):
        missing.append("cylindrical base")

    if not feats:
        if any(word in low_t for word in ("отверст", "крепеж")):
            require(_method_present(low_c, "hole", "pattern_holes_circular", "pattern_holes_linear", "pattern_holes_points", "pattern_holes_rect", "hole_list"), "hole")
        if any(word in low_t for word in ("карман", "углублен", "выборк")):
            require(_method_present(low_c, "pocket", "cut"), "pocket")
        if any(word in low_t for word in ("канавк", "проточк")):
            require(_method_present(low_c, "ring_groove", "groove") or (low_c.count("circle(") >= 2 and "part.cut(" in low_c), "groove")
        if "фаск" in low_t or "chamfer" in low_t:
            require(_method_present(low_c, "chamfer", "chamfer_edge"), "chamfer")
        if "скругл" in low_t or "fillet" in low_t:
            require(_method_present(low_c, "fillet", "fillet_edge"), "fillet")
        if "шпоноч" in low_t or re.search(r"\bпаз\b", low_t):
            require(_method_present(low_c, "slot", "keyway"), "slot/keyway")

    return list(dict.fromkeys(missing))


def must_fix_holes(code: str) -> bool:
    return False
