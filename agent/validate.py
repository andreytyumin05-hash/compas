"""Static safety and API-contract validation for generated CAD scripts."""

from __future__ import annotations

import ast
import re
from typing import List, Tuple

_ALLOWED_FROM = {("core", "Part")}
_PART_METHODS = {
    "create", "sketch", "sketch_on_face", "extrude", "cut", "revolve", "get_edges",
    "chamfer", "fillet", "fillet_edge", "chamfer_edge", "hole", "pattern_holes_circular",
    "pattern_holes_rect", "pattern_holes_points", "pattern_holes_linear", "hole_list",
    "mirror_points", "slot", "step", "boss", "hex_boss", "ring_groove", "groove",
    "keyway", "pocket", "counterbore", "countersink", "export", "export_formats", "close",
    "mass_properties", "update", "name", "var", "set_properties", "get_context", "set_view", "screenshot",
}
_SKETCH_METHODS = {
    "circle", "line", "arc", "rectangle", "rounded_rect", "stadium", "ellipse", "polygon",
    "polyline", "arc_by_points", "spline", "bezier", "slot", "dim_linear", "dim_radial", "dim_rect",
}
_FORBIDDEN_NAMES = {"win32com", "pythoncom", "gencache", "Dispatch", "GetActiveObject"}
_FORBIDDEN_CALLS = {"loft", "sweep", "shell", "thread"}
_NEG_NUM = re.compile(r"(?:depth|diameter|radius|width|height|pcd|length|thickness)\s*=\s*-\s*\d", re.I)


def _call_name(node: ast.Call) -> Tuple[str | None, str | None]:
    if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
        return node.func.value.id, node.func.attr
    return None, None


def validate_generated_code(code: str) -> Tuple[bool, List[str]]:
    errors: List[str] = []
    if not code or not code.strip():
        return False, ["пустой код"]
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, [f"синтаксис: {exc}"]

    part_creates = 0
    part_updates = 0
    imports_checked = False
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                errors.append(f"запрещённый import: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            imports_checked = True
            module = node.module or ""
            names = tuple(alias.name for alias in node.names)
            if (module, names[0] if len(names) == 1 else "") not in _ALLOWED_FROM:
                errors.append(f"разрешён только `from core import Part`, найдено: from {module} import {', '.join(names)}")
        elif isinstance(node, ast.Call):
            owner, method = _call_name(node)
            if owner == "Part" and method == "create":
                part_creates += 1
            if owner == "part" and method == "update":
                part_updates += 1
            if owner == "part" and method and method not in _PART_METHODS:
                errors.append(f"неизвестный part.{method}() — такого метода нет в core")
            if owner == "sk" and method and method not in _SKETCH_METHODS:
                errors.append(f"неизвестный sk.{method}() — такого метода нет в core")
            if method in _FORBIDDEN_CALLS:
                errors.append(f"операция {method}() пока не реализована в core и запрещена в generated code")
        elif isinstance(node, ast.Name) and node.id in _FORBIDDEN_NAMES:
            errors.append(f"запрещённый COM-доступ: {node.id}")

    if not imports_checked:
        errors.append("нужен импорт: from core import Part")
    if part_creates == 0:
        errors.append("ожидается Part.create(...)")
    elif part_creates > 1:
        errors.append("Part.create(...) должен вызываться один раз для одной детали")
    if part_updates == 0:
        errors.append("нужен part.update() в конце построения")
    if _NEG_NUM.search(code):
        errors.append("отрицательный размер")
    return (len(set(errors)) == 0, list(dict.fromkeys(errors)))


def critic_warnings(code: str, task: str = "") -> List[str]:
    warnings: List[str] = []
    low_code = (code or "").lower()
    low_task = (task or "").lower()
    if "part.var(" not in low_code and any(x in low_task for x in ("диаметр", "длина", "ширина", "высота", "толщин", "размер")):
        warnings.append("важные размеры не вынесены в part.var()")
    if "part.update(" not in low_code:
        warnings.append("нет part.update()")
    if any(x in low_task for x in ("крышк", "фланец", "отверст")) and "screenshot(" not in low_code:
        warnings.append("нет явного screenshot; live verifier добавит контрольный кадр")
    if "цеков" in low_task and "counterbore(" not in low_code:
        warnings.append("цековка должна быть реализована через counterbore()")
    if any(x in low_task for x in ("резьб", "thread", "shell", "оболоч")):
        warnings.append("thread/shell ещё не моделируются нативно и не должны имитироваться")
    return list(dict.fromkeys(warnings))
