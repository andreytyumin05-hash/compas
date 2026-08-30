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
# проза только если нет валидного Part.create (иначе extract мог вырезать код)
_PROSE = re.compile(
    r"\b(we need|the user|produce only|corrected code|here is|let's|i will)\b",
    re.I,
)


def validate_generated_code(code: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not code or not code.strip():
        return False, ["пустой код"]

    # если есть нормальный импорт и create — прозу в хвосте игнорируем после extract
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
