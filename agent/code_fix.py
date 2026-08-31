"""Нормализация кода + проверка покрытия ТЗ (без ложных срабатываний)."""

from __future__ import annotations

import ast
import re
import textwrap
from typing import List, Set


def normalize_code(code: str) -> str:
    code = code.replace("\r\n", "\n").replace("\t", "    ").strip()
    try:
        ded = textwrap.dedent(code)
        if _can_parse(ded):
            return ded.strip() + "\n"
    except Exception:
        pass
    return code if code.endswith("\n") else code + "\n"


def _can_parse(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def semantic_warnings(code: str) -> List[str]:
    return []


def must_fix_holes(code: str) -> bool:
    lower = code.lower()
    if (
        "rectangle(" in lower
        and "circle(" in lower
        and "cut(" not in lower
        and "hole(" not in lower
    ):
        return True
    return False


def _feature_types_from_task(task: str) -> Set[str]:
    found = set()
    for m in re.finditer(r"feature\s*=\s*([a-z_]+)", task or "", flags=re.I):
        found.add(m.group(1).lower())
    m = re.search(r"required_features\s*=\s*([a-z_,\s]+)", task or "", flags=re.I)
    if m:
        for part in m.group(1).split(","):
            p = part.strip().lower()
            if p:
                found.add(p)
    return found


def check_task_feature_requirements(task: str, code: str) -> List[str]:
    low_t = (task or "").lower()
    low_c = (code or "").lower()
    missing: List[str] = []

    if not low_t.strip() or not low_c.strip():
        return missing

    filtered_lines = []
    for ln in low_t.splitlines():
        s = ln.strip()
        if s.startswith("ops_order="):
            continue
        if s.startswith("правило:"):
            continue
        if s.startswith("порядок:"):
            continue
        filtered_lines.append(s)
    low_t = "\n".join(filtered_lines)

    feats = _feature_types_from_task(task)

    def has_hole_ops() -> bool:
        return any(x in low_c for x in ("hole(", "pattern_holes"))

    def has_pocket_ops() -> bool:
        # pattern_holes ≠ карман
        return any(
            x in low_c for x in ("cut(", "pocket(", "ring_groove(", "groove(")
        ) or ("polygon(" in low_c and "cut(" in low_c)

    if feats & {"pocket", "hex_pocket", "recess"}:
        if not has_pocket_ops():
            missing.append("pocket")
        elif feats & {"hex_pocket"} and "polygon(" not in low_c and "hex_" not in low_c:
            if "cut(" not in low_c and "pocket(" not in low_c:
                missing.append("hex_pocket")

    if feats & {"hole", "pattern_holes"}:
        if not has_hole_ops() and "cut(" not in low_c:
            missing.append("hole")

    if feats & {"groove"}:
        if "ring_groove(" not in low_c and "groove(" not in low_c:
            if not (low_c.count("circle(") >= 2 and "cut(" in low_c):
                missing.append("groove")

    if feats & {"counterbore"}:
        if "counterbore(" not in low_c:
            if low_c.count("hole(") + low_c.count("cut(") < 2:
                missing.append("counterbore")

    if feats & {"chamfer"} and "chamfer(" not in low_c:
        missing.append("chamfer")
    if feats & {"fillet"} and "fillet(" not in low_c:
        missing.append("fillet")

    if feats & {"slot", "keyway"}:
        if "slot(" not in low_c and "keyway(" not in low_c:
            missing.append("slot")

    if feats & {"step", "boss"} or "body_style=cylindrical_steps" in low_t:
        n_ext = low_c.count("extrude(") + low_c.count("part.step(") + low_c.count("part.boss(")
        if n_ext < 2:
            missing.append("несколько extrude (ступени)")

    if not feats:
        if any(w in low_t for w in ("карман", "шестигранн", "углублен")):
            if not has_pocket_ops():
                missing.append("pocket")
        if any(w in low_t for w in ("отверст", "крепежн")):
            if not has_hole_ops() and "cut(" not in low_c:
                missing.append("hole")
        if any(w in low_t for w in ("канавк", "проточк")):
            if "ring_groove(" not in low_c and "groove(" not in low_c:
                if not (low_c.count("circle(") >= 2 and "cut(" in low_c):
                    missing.append("groove")
        if re.search(r"\bфаск", low_t) or "chamfer" in low_t:
            if "chamfer(" not in low_c:
                missing.append("chamfer")
        if re.search(r"\bскругл", low_t) or "fillet" in low_t:
            if "fillet(" not in low_c:
                missing.append("fillet")
        if any(w in low_t for w in ("паз", "шпоноч")):
            if "slot(" not in low_c and "keyway(" not in low_c:
                missing.append("slot")
        if any(w in low_t for w in ("ступен", "уступ", "пробк")) or re.search(
            r"\bвал\b", low_t
        ):
            if low_c.count("extrude(") < 2 and "step(" not in low_c:
                missing.append("несколько extrude (ступени)")

        rich = any(
            w in low_t
            for w in ("ступен", "бобыш", "карман", "отверст", "фаск", "скругл")
        )
        if (
            rich
            and low_c.count("extrude(") <= 1
            and not has_pocket_ops()
            and not has_hole_ops()
            and "step(" not in low_c
        ):
            missing.append("feature_tree")

    return list(dict.fromkeys(missing))
