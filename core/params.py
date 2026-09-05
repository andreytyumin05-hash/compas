"""Named parameters and live KOMPAS variable access."""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any, Dict, Optional, Set

_BINOPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_ALLOWED_CALLS = {"abs": abs, "min": min, "max": max, "sqrt": math.sqrt}

class ParamError(ValueError):
    pass

class ParamStore:
    def __init__(self) -> None:
        self._raw: Dict[str, float | str] = {}
        self._cache: Dict[str, float] = {}
    @staticmethod
    def _name(name: str) -> str:
        value = str(name).strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", value):
            raise ParamError(f"недопустимое имя параметра: {name!r}")
        return value
    def set(self, name: str, value: Any = None, *, expr: Optional[str] = None) -> None:
        key = self._name(name)
        if expr is not None:
            expression = str(expr).strip()
            if not expression:
                raise ParamError(f"параметр {key}: пустое выражение")
            self._raw[key] = expression
        elif isinstance(value, str):
            expression = value.strip()
            try: numeric = float(expression)
            except ValueError:
                if not expression: raise ParamError(f"параметр {key}: пустое значение")
                self._raw[key] = expression
            else:
                if not math.isfinite(numeric): raise ParamError(f"параметр {key}: число не finite")
                self._raw[key] = numeric
        elif value is not None:
            numeric = float(value)
            if not math.isfinite(numeric): raise ParamError(f"параметр {key}: число не finite")
            self._raw[key] = numeric
        else: raise ParamError(f"параметр {key}: нужен value или expr")
        self._cache.clear()
    def names(self) -> list[str]: return sorted(self._raw)
    def dependencies(self, name: str) -> Set[str]:
        key = self._name(name); raw = self._raw.get(key)
        if not isinstance(raw, str): return set()
        try: tree = ast.parse(raw, mode="eval")
        except SyntaxError as exc: raise ParamError(f"параметр {key}: неверное выражение {raw!r}") from exc
        return {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    def dependency_graph(self) -> Dict[str, Set[str]]:
        graph = {name: self.dependencies(name) for name in self._raw}
        unknown = sorted({dep for deps in graph.values() for dep in deps if dep not in graph})
        if unknown: raise ParamError("неизвестные зависимости: " + ", ".join(unknown))
        return graph
    def eval(self, name: str, *, _stack: Optional[Set[str]] = None) -> float:
        key = self._name(name)
        if key in self._cache: return self._cache[key]
        if key not in self._raw: raise ParamError(f"неизвестный параметр {key}")
        stack = set(_stack or set())
        if key in stack: raise ParamError(f"цикл зависимостей: {key}")
        stack.add(key); raw = self._raw[key]
        value = float(raw) if not isinstance(raw, str) else self._eval_expr(raw, stack)
        if not math.isfinite(value): raise ParamError(f"параметр {key}: результат не finite")
        self._cache[key] = value; return value
    def _eval_expr(self, expression: str, stack: Set[str]) -> float:
        try: tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc: raise ParamError(f"неверное выражение: {expression!r}") from exc
        def node_value(node: ast.AST) -> float:
            if isinstance(node, ast.Expression): return node_value(node.body)
            if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return float(node.value)
            if isinstance(node, ast.Name): return self.eval(node.id, _stack=stack)
            if isinstance(node, ast.BinOp) and type(node.op) in _BINOPS: return float(_BINOPS[type(node.op)](node_value(node.left), node_value(node.right)))
            if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY: return float(_UNARY[type(node.op)](node_value(node.operand)))
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in _ALLOWED_CALLS:
                args = [node_value(arg) for arg in node.args]
                if node.func.id in {"abs", "sqrt"} and len(args) != 1: raise ParamError(f"неверное число аргументов: {expression!r}")
                if node.func.id in {"min", "max"} and not args: raise ParamError(f"пустой min/max: {expression!r}")
                return float(_ALLOWED_CALLS[node.func.id](*args))
            raise ParamError(f"неподдерживаемое выражение: {expression!r}")
        try: return float(node_value(tree))
        except (ZeroDivisionError, ValueError, OverflowError) as exc: raise ParamError(f"ошибка вычисления {expression!r}: {exc}") from exc
    def eval_all(self) -> Dict[str, float]:
        self.dependency_graph(); return {name: self.eval(name) for name in self.names()}
    def get(self, name: str, default: Optional[float] = None) -> float:
        try: return self.eval(name)
        except ParamError:
            if default is not None: return default
            raise
    def __getitem__(self, name: str) -> float: return self.eval(name)

def _variable_collection(part: Any) -> Any:
    owner = getattr(part, "_part", None) or part
    collection = getattr(owner, "VariableCollection", None)
    return collection() if callable(collection) else collection

def _iter_collection(collection: Any):
    if collection is None: return
    count = getattr(collection, "Count", None)
    if callable(count): count = count()
    if count is None: return
    for i in range(int(count)):
        for getter in ("Item", "GetItem"):
            fn = getattr(collection, getter, None)
            if callable(fn):
                try:
                    item = fn(i)
                    if item is not None: yield item
                    break
                except Exception: continue

def list_kompas_variables(part: Any) -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    try:
        for variable in _iter_collection(_variable_collection(part)):
            name = str(getattr(variable, "name", None) or getattr(variable, "Name", "")).strip()
            if not name: continue
            value = getattr(variable, "value", None)
            if value is None: value = getattr(variable, "Value", None)
            expression = getattr(variable, "Expression", None)
            if expression is None: expression = getattr(variable, "expression", None)
            note = getattr(variable, "note", None)
            if note is None: note = getattr(variable, "Note", "")
            result[name] = {"value": value, "expression": expression, "note": note}
    except Exception: return {}
    return result

def set_kompas_variable(part: Any, name: str, value: Any = None, *, expression: Optional[str] = None) -> bool:
    key = str(name).strip()
    if not key: raise ParamError("пустое имя переменной")
    collection = _variable_collection(part)
    if collection is None: return False
    variable = None
    for candidate in _iter_collection(collection):
        candidate_name = str(getattr(candidate, "name", None) or getattr(candidate, "Name", "")).strip()
        if candidate_name == key:
            variable = candidate; break
    if variable is None:
        for getter in ("GetByName", "Find"):
            fn = getattr(collection, getter, None)
            if callable(fn):
                try:
                    variable = fn(key)
                    if variable is not None: break
                except Exception: pass
    if variable is None: raise ParamError(f"переменная {key!r} не найдена в открытой модели")
    if expression is not None:
        expression = str(expression).strip()
        for attr in ("Expression", "expression"):
            try: setattr(variable, attr, expression); return True
            except Exception: pass
        return False
    numeric = float(value)
    if not math.isfinite(numeric): raise ParamError("значение переменной не finite")
    for attr in ("value", "Value"):
        try: setattr(variable, attr, numeric); return True
        except Exception: pass
    return False

def sync_kompas_variable(part: Any, name: str, value: float, *, note: str = "") -> bool:
    try:
        collection = _variable_collection(part)
        if collection is None: return False
        try: variable = next(v for v in _iter_collection(collection) if str(getattr(v, "name", None) or getattr(v, "Name", "")).strip() == str(name))
        except StopIteration: variable = None
        if variable is None:
            for getter in ("GetByName", "Find"):
                fn = getattr(collection, getter, None)
                if callable(fn):
                    try:
                        variable = fn(str(name))
                        if variable is not None: break
                    except Exception: pass
        if variable is None:
            add = getattr(collection, "AddNewVariable", None)
            if not callable(add): return False
            variable = add(str(name), float(value), str(note))
        if variable is None: return False
        for attr in ("value", "Value"):
            try: setattr(variable, attr, float(value)); break
            except Exception: continue
        if note:
            for attr in ("note", "Note"):
                try: setattr(variable, attr, str(note)); break
                except Exception: continue
        return True
    except Exception: return False
