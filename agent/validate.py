"""Статическая проверка сгенерированного кода."""

from __future__ import annotations

import ast
import re
from typing import List, Tuple

_ALLOWED_IMPORT = re.compile(
    r"^\s*from\s+core\s+import\s+Part\s*$"
)

# методы, которые можно звать у part / sk
_PART_METHODS = {
    "create",
    "sketch",
    "extrude",
    "cut",
    "revolve",
    "chamfer",
    "fillet",
    "update",
    "name",
}
_SKETCH_METHODS = {
    "circle",
    "rectangle",
    "line",
    "polygon",
    "arc",
    "slot",
}


def validate_generated_code(code: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []

    if not code or not code.strip():
        return False, ["пустой код"]

    try:
        tree = ast.parse(code)
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
    for b in banned:
        if b in code:
            errors.append(f"запрещено: {b}")

    return (len(errors) == 0, errors)
