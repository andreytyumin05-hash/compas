"""Статическая проверка сгенерированного кода."""

from __future__ import annotations

import ast
import re
from typing import List, Tuple

_ALLOWED_IMPORT = re.compile(r"^\s*from\s+core\s+import\s+Part\s*$")

# depth=/diameter=/radius= отрицательные или нулевые — частые баги
_NEG_NUM = re.compile(
    r"(?:depth|diameter|radius|width|height|pcd)\s*=\s*-\s*\d",
    re.I,
)
_ZERO_DEPTH = re.compile(r"extrude\s*\([^)]*depth\s*=\s*0\s*[,)]", re.I)


def validate_generated_code(code: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not code or not code.strip():
        return False, ["пустой код"]

    try:
        ast.parse(code)
    except SyntaxError as e:
        return False, [f"синтаксис: {e}"]

    has_import = False
    has_create = False

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

    if "Part.create" in code:
        has_create = True

    if not has_import:
        errors.append("нужен ровно: from core import Part")
    if not has_create:
        errors.append("ожидается Part.create(...)")

    banned = ("win32com", "gencache", "Dispatch", "GetActiveObject", "diameter=")
    # diameter= разрешён в hole(diameter=...) — уберём ложный banned
    for b in ("win32com", "gencache", "Dispatch", "GetActiveObject"):
        if b in code:
            errors.append(f"запрещено: {b}")

    if _NEG_NUM.search(code):
        errors.append("отрицательный размер (depth/diameter/radius/…)")
    if _ZERO_DEPTH.search(code):
        errors.append("extrude с depth=0")

    return (len(errors) == 0, errors)
