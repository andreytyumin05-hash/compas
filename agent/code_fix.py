"""Нормализация и лёгкий ремонт кода от LLM."""

from __future__ import annotations

import ast
import re
import textwrap
from typing import List, Tuple


def normalize_code(code: str) -> str:
    """Убрать markdown-хвосты, выровнять отступы, чтобы exec не падал."""
    code = code.replace("\r\n", "\n").replace("\t", "    ")
    code = code.strip()

    # случай: все строки с общим отступом
    try:
        ded = textwrap.dedent(code)
        if _can_parse(ded):
            return ded.strip() + "\n"
    except Exception:
        pass

    lines = code.split("\n")
    nonempty = [ln for ln in lines if ln.strip()]
    if not nonempty:
        return code + "\n"

    # минимальный отступ среди строк, которые начинаются с пробела
    spaced = [len(ln) - len(ln.lstrip(" ")) for ln in nonempty if ln.startswith(" ")]
    if spaced:
        m = min(spaced)
        if m > 0:
            fixed = []
            for ln in lines:
                if ln.startswith(" " * m):
                    fixed.append(ln[m:])
                else:
                    fixed.append(ln)
            candidate = "\n".join(fixed).strip() + "\n"
            if _can_parse(candidate):
                return candidate

    # первая строка без отступа, остальные с лишними пробелами
    if nonempty and not nonempty[0].startswith(" "):
        indents = [
            len(ln) - len(ln.lstrip(" "))
            for ln in nonempty[1:]
            if ln.startswith(" ")
        ]
        if indents:
            m = min(indents)
            fixed = [lines[0]] if lines else []
            for ln in lines[1:]:
                if ln.startswith(" " * m):
                    fixed.append(ln[m:])
                else:
                    fixed.append(ln.lstrip(" ") if ln.startswith(" ") else ln)
            # rebuild carefully
            fixed = []
            for i, ln in enumerate(lines):
                if i == 0:
                    fixed.append(ln)
                elif ln.startswith(" " * m):
                    fixed.append(ln[m:])
                else:
                    fixed.append(ln)
            candidate = "\n".join(fixed).strip() + "\n"
            if _can_parse(candidate):
                return candidate

    return code if code.endswith("\n") else code + "\n"


def _can_parse(code: str) -> bool:
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def semantic_warnings(code: str) -> List[str]:
    """
    Мягкие проверки логики (не блокируют, если validate уже OK,
    но build может требовать исправления).
    """
    warns: List[str] = []
    lower = code.lower()

    has_circle = "circle(" in lower
    has_extrude = "extrude(" in lower
    has_cut = "cut(" in lower

    # отверстия без выреза — частая ошибка LLM
    if has_circle and has_extrude and not has_cut:
        # втулка: два circle + один extrude иногда валидна, но для плиты — нет
        # эвристика: rectangle + circle без cut
        if "rectangle(" in lower:
            warns.append(
                "есть rectangle и circle, но нет part.cut — отверстия не будут вырезаны"
            )
        elif lower.count("circle(") >= 2 and "through_all" not in lower:
            # два концентрических circle + extrude — ок для трубы; иначе намекнуть
            pass

    if has_circle and "rectangle(" in lower and has_extrude and not has_cut:
        warns.append("после эскиза отверстий нужен part.cut(..., through_all=True)")

    return warns


def must_fix_holes(code: str) -> bool:
    """Жёстко: плита/основание + отверстия без cut."""
    lower = code.lower()
    if "rectangle(" in lower and "circle(" in lower and "cut(" not in lower:
        return True
    return False
