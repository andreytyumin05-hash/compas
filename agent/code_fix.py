"""Нормализация кода + проверка покрытия ТЗ (без ложных срабатываний)."""

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
    if "rectangle(" in lower and "circle(" in lower and "cut(" not in lower and "hole(" not in lower:
        return True
    return False


def check_task_feature_requirements(task: str, code: str) -> List[str]:
    """
    Требуем операции только по явным маркерам ТЗ.
    Не путать «глубиной 6» в цековке с обязательным pocket, если есть hole.
    """
    low_t = (task or "").lower()
    low_c = (code or "").lower()
    missing: List[str] = []

    if not low_t.strip() or not low_c.strip():
        return missing

    # Явный карман / глухой вырез (не просто слово «глубина» у отверстия)
    wants_pocket = any(
        w in low_t
        for w in ("карман", "pocket", "выборк", "шестигранн", "углублен")
    ) or ("глух" in low_t and "вырез" in low_t)
    if wants_pocket:
        if "cut(" not in low_c and "hole(" not in low_c:
            missing.append("cut/pocket")

    # Отверстия
    wants_hole = any(
        w in low_t for w in ("отверст", "hole", "pattern_holes", "крепежн")
    )
    if wants_hole:
        if not any(
            x in low_c
            for x in ("hole(", "pattern_holes", "cut(")
        ):
            missing.append("hole")

    # Несколько цилиндрических ступеней → несколько extrude
    wants_steps = any(
        w in low_t for w in ("ступен", "уступ", "step", "пробк", "вал ")
    ) or low_t.count("feature=step") + low_t.count("feature=boss") >= 1
    if wants_steps:
        n_ext = low_c.count("extrude(")
        if n_ext < 2:
            missing.append("несколько extrude (ступени)")

    # Фаска / скругление — только если явно
    if re.search(r"\bфаск", low_t) or "chamfer" in low_t:
        if "chamfer(" not in low_c and "fillet(" not in low_c:
            missing.append("chamfer")
    if re.search(r"\bскругл", low_t) or "fillet" in low_t:
        if "fillet(" not in low_c and "chamfer(" not in low_c:
            missing.append("fillet")

    # Только одна база при богатом ТЗ
    rich = any(
        w in low_t
        for w in (
            "ступен",
            "бобыш",
            "карман",
            "отверст",
            "фаск",
            "скругл",
            "feature=",
        )
    )
    if rich and low_c.count("extrude(") <= 1 and "cut(" not in low_c and "hole(" not in low_c:
        missing.append("feature_tree")

    return list(dict.fromkeys(missing))
