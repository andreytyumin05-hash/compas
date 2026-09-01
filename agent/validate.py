"""Статическая проверка кода."""

from __future__ import annotations

import ast
import re
from typing import List, Tuple

_ALLOWED_IMPORT = re.compile(r"^\s*from\s+core\s+import\s+Part\s*$")
_NEG_NUM = re.compile(
    r"(?:depth|diameter|radius|width|height|pcd)\s*=\s*-\s*\d",
    re.I,
)
_ZERO_DEPTH = re.compile(r"extrude\s*\([^)]*depth\s*=\s*0\s*[,)]", re.I)
_PROSE = re.compile(
    r"\b(we need|the user|produce only|corrected code|here is|let's|i will)\b",
    re.I,
)


def validate_generated_code(code: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not code or not code.strip():
        return False, ["пустой код"]

    if _PROSE.search(code) and "Part.create" not in code:
        return False, ["английская проза вместо Python"]

    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, [f"синтаксис: {e}"]

    has_import = False
    has_create = "Part.create" in code

    for line in code.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("import ") and "core" not in s:
            errors.append(f"запрещённый import: {s}")
        if s.startswith("from ") and not s.startswith("from core import"):
            errors.append(f"запрещённый from: {s}")
        if _ALLOWED_IMPORT.match(line):
            has_import = True

    if not has_import:
        errors.append("нужен: from core import Part")
    if not has_create:
        errors.append("ожидается Part.create(...)")

    for b in ("win32com", "gencache", "Dispatch", "GetActiveObject"):
        if b in code:
            errors.append(f"запрещено: {b}")

    if _NEG_NUM.search(code):
        errors.append("отрицательный размер")
    if _ZERO_DEPTH.search(code):
        errors.append("extrude depth=0")

    return (len(errors) == 0, errors)


def critic_warnings(code: str, task: str = "") -> List[str]:
    """
    Мягкие предупреждения Visual Fluent (не блокируют build).
    - нет part.var при нескольких размерах в ТЗ
    - нет set_properties
    - нет screenshot / set_view на сложных задачах
    """
    warnings: List[str] = []
    c = code or ""
    t = (task or "").lower()

    if not c.strip():
        return warnings

    n_var = c.count("part.var(") + c.count(".var(")
    has_props = "set_properties(" in c
    has_shot = "screenshot(" in c
    has_view = "set_view(" in c

    # несколько чисел в ТЗ → желательны переменные
    nums = re.findall(r"\b\d{1,4}(?:[.,]\d+)?\b", t)
    if len(nums) >= 3 and n_var == 0:
        warnings.append("желательно part.var(...) для ключевых размеров")

    if len(t) > 40 and not has_props:
        warnings.append("желательно part.set_properties(designation=..., name=...)")

    complexish = any(
        w in t
        for w in ("build_plan", "ступен", "пробк", "feature=", "карман", "бобыш")
    )
    if complexish and not has_shot and not has_view:
        warnings.append("желательно set_view + screenshot для visual loop")

    return warnings
