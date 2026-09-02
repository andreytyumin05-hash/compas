"""Синтаксис + allowlist из core.ops_registry."""

from __future__ import annotations

import ast
import re
from typing import List, Tuple

from core.ops_registry import allowed_part_methods, unsupported_part_methods

_FORBIDDEN = (
    "win32com",
    "gencache",
    "Dispatch",
    "GetActiveObject",
    "pythoncom",
)


def validate_generated_code(code: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not (code or "").strip():
        return False, ["пустой код"]

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        return False, [f"синтаксис: {e}"]

    if "from core import Part" not in code and "Part.create" not in code:
        errors.append("нет from core import Part / Part.create")

    if "part.update(" not in code:
        errors.append("нет part.update()")

    low = code.lower()
    for bad in _FORBIDDEN:
        if bad.lower() in low:
            errors.append(f"запрещённый фрагмент: {bad}")

    allowed = allowed_part_methods()
    unsupported = unsupported_part_methods()
    calls = re.findall(r"\bpart\.([A-Za-z_]\w*)\s*\(", code)
    for name in calls:
        if name in unsupported:
            errors.append(f"unsupported part.{name}() — запрещено registry")
        elif name not in allowed:
            errors.append(f"неизвестный part.{name}()")

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                if "win32" in a.name.lower():
                    errors.append(f"import {a.name}")
        if isinstance(node, ast.ImportFrom) and node.module and "win32" in node.module.lower():
            errors.append(f"from {node.module}")

    return (len(errors) == 0, list(dict.fromkeys(errors)))
