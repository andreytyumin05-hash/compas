"""Именованные параметры и граф зависимостей (PARAMETER DEPENDENCY)."""

from __future__ import annotations

import ast
import math
import operator
import re
from typing import Any, Dict, List, Optional, Set

_BINOPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class ParamError(ValueError):
    pass


class ParamStore:
    def __init__(self) -> None:
        self._raw: Dict[str, Any] = {}
        self._cache: Dict[str, float] = {}

    def set(self, name: str, value: Any = None, *, expr: Optional[str] = None) -> None:
        name = _norm_name(name)
        if expr is not None:
            self._raw[name] = str(expr).strip()
        elif value is not None:
            if isinstance(value, str) and _looks_like_expr(value):
                self._raw[name] = value.strip()
            else:
                self._raw[name] = float(value)
        else:
            raise ParamError(f"param {name}: нужен value или expr")
        self._cache.clear()

    def names(self) -> List[str]:
        return sorted(self._raw.keys())

    def dependencies(self, name: str) -> Set[str]:
        name = _norm_name(name)
        raw = self._raw.get(name)
        if raw is None or not isinstance(raw, str):
            return set()
        return _expr_names(raw)

    def dependency_graph(self) -> Dict[str, Set[str]]:
        return {n: self.dependencies(n) for n in self._raw}

    def eval(self, name: str, *, _stack: Optional[Set[str]] = None) -> float:
        name = _norm_name(name)
        if name in self._cache:
            return self._cache[name]
        if name not in self._raw:
            raise ParamError(f"неизвестный параметр {name}")
        stack = set(_stack or set())
        if name in stack:
            raise ParamError(f"цикл зависимостей: {name}")
        stack.add(name)
        raw = self._raw[name]
        if isinstance(raw, (int, float)):
            val = float(raw)
        else:
            val = _eval_expr(str(raw), self, stack)
        self._cache[name] = val
        return val

    def eval_all(self) -> Dict[str, float]:
        return {n: self.eval(n) for n in self.names()}

    def get(self, name: str, default: Optional[float] = None) -> float:
        try:
            return self.eval(name)
        except ParamError:
            if default is not None:
                return default
            raise

    def __getitem__(self, name: str) -> float:
        return self.eval(name)


def _norm_name(name: str) -> str:
    n = str(name).strip()
    if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", n):
        raise ParamError(f"недопустимое имя параметра: {name!r}")
    return n


def _looks_like_expr(s: str) -> bool:
    return bool(re.search(r"[A-Za-z_/+\-*]", s)) and not re.fullmatch(
        r"[-+]?\d+(\.\d+)?", s.strip()
    )


def _expr_names(expr: str) -> Set[str]:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError:
        return set()
    return {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}


def _eval_expr(expr: str, store: ParamStore, stack: Set[str]) -> float:
    try:
        tree = ast.parse(expr, mode="eval")
    except SyntaxError as e:
        raise ParamError(f"выражение {expr!r}: {e}") from e

    def _node(n: ast.AST) -> float:
        if isinstance(n, ast.Expression):
            return _node(n.body)
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)):
            return float(n.value)
        if isinstance(n, ast.Name):
            return store.eval(n.id, _stack=stack)
        if isinstance(n, ast.BinOp) and type(n.op) in _BINOPS:
            return float(_BINOPS[type(n.op)](_node(n.left), _node(n.right)))
        if isinstance(n, ast.UnaryOp) and type(n.op) in _UNARY:
            return float(_UNARY[type(n.op)](_node(n.operand)))
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
            fn = n.func.id
            args = [_node(a) for a in n.args]
            if fn == "abs" and len(args) == 1:
                return abs(args[0])
            if fn == "min":
                return min(args)
            if fn == "max":
                return max(args)
            if fn == "sqrt" and len(args) == 1:
                return math.sqrt(args[0])
        raise ParamError(f"неподдерживаемое выражение: {expr!r}")

    return float(_node(tree))
