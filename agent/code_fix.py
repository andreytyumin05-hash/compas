"""Нормализация кода + проверка покрытия ТЗ."""

from __future__ import annotations

import ast
import re
import textwrap
from typing import List


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


def check_task_feature_requirements(task: str, code: str) -> List[str]:
    low_t = (task or "").lower()
    low_c = (code or "").lower()
    missing: List[str] = []

    if not low_t.strip() or not low_c.strip():
        return missing

    wants_pocket = any(
        w in low_t for w in ("карман", "pocket", "выборк", "шестигранн", "углублен")
    ) or ("глух" in low_t and "вырез" in low_t)
    if wants_pocket:
        if (
            "cut(" not in low_c
            and "hole(" not in low_c
            and "pocket(" not in low_c
        ):
            missing.append("pocket")

    wants_hole = any(
        w in low_t for w in ("отверст", "hole", "pattern_holes", "крепежн")
    )
    if wants_hole:
        if not any(x in low_c for x in ("hole(", "pattern_holes", "cut(")):
            missing.append("hole")

    wants_steps = any(
        w in low_t for w in ("ступен", "уступ", "step", "пробк", "вал ")
    ) or low_t.count("feature=step") + low_t.count("feature=boss") >= 1
    if wants_steps:
        n_ext = low_c.count("extrude(") + low_c.count("part.step(")
        if n_ext < 2 and "part.step(" not in low_c:
            # один step() может быть ок если есть base extrude + step
            if low_c.count("extrude(") < 1:
                missing.append("step")
            elif low_c.count("extrude(") < 2 and "step(" not in low_c:
                missing.append("несколько extrude (ступени)")

    if any(w in low_t for w in ("паз", "slot", "шпоноч")):
        if "slot(" not in low_c and "keyway(" not in low_c:
            missing.append("slot")

    if re.search(r"\bфаск", low_t) or "chamfer" in low_t:
        if "chamfer(" not in low_c and "fillet(" not in low_c:
            missing.append("chamfer")
    if re.search(r"\bскругл", low_t) or "fillet" in low_t:
        if "fillet(" not in low_c and "chamfer(" not in low_c:
            missing.append("fillet")

    rich = any(
        w in low_t
        for w in ("ступен", "бобыш", "карман", "отверст", "фаск", "скругл", "feature=")
    )
    if (
        rich
        and low_c.count("extrude(") <= 1
        and "cut(" not in low_c
        and "hole(" not in low_c
        and "step(" not in low_c
    ):
        missing.append("feature_tree")

    return list(dict.fromkeys(missing))
