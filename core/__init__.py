"""KOMPAS-3D Python facade used by generated CAD scripts."""

from .connection import KompasApp, get_app
from .part import Part
from .sketch import Sketch
from .exceptions import KompasError, KompasNotRunningError, KompasOperationError
from .params import ParamStore, ParamError, sync_kompas_variable, list_kompas_variables, set_kompas_variable
from .sketch_spline import apply_spline_patch
from .sketch_auto import apply_auto_dimension_patch

apply_spline_patch()
apply_auto_dimension_patch()


def _ensure_params(self) -> ParamStore:
    store = getattr(self, "_params", None)
    if store is None:
        store = ParamStore()
        self._params = store
    return store


def param(self, name: str, value=None, *, expr: str | None = None, note: str = ""):
    store = _ensure_params(self)
    store.set(name, value, expr=expr)
    try:
        evaluated = store.eval(name)
    except ParamError:
        return self
    sync_kompas_variable(self, name, evaluated, note=note)
    return self


def p(self, name: str) -> float:
    return _ensure_params(self).eval(name)


def params_dict(self):
    return _ensure_params(self).eval_all()


def param_graph(self):
    return _ensure_params(self).dependency_graph()


def variables(self):
    return list_kompas_variables(self)


def set_variable(self, name: str, value=None, *, expression: str | None = None):
    return set_kompas_variable(self, name, value, expression=expression)


Part.param = param  # type: ignore[attr-defined]
Part.p = p  # type: ignore[attr-defined]
Part.params_dict = params_dict  # type: ignore[attr-defined]
Part.param_graph = param_graph  # type: ignore[attr-defined]
Part.variables = variables  # type: ignore[attr-defined]
Part.set_variable = set_variable  # type: ignore[attr-defined]


def _no_sketch_on_face(self, *args, **kwargs):
    raise KompasOperationError("sketch_on_face: реальный выбор грани ещё не реализован")


def _no_shell(self, *args, **kwargs):
    raise KompasOperationError("shell: реальная native shell-операция ещё не реализована")


def _no_thread(self, *args, **kwargs):
    raise KompasOperationError("thread: реальная native thread-операция ещё не реализована")

Part.sketch_on_face = _no_sketch_on_face  # type: ignore[attr-defined]
Part.shell = _no_shell  # type: ignore[attr-defined]
Part.thread = _no_thread  # type: ignore[attr-defined]

__all__ = [
    "KompasApp", "get_app", "Part", "Sketch", "KompasError",
    "KompasNotRunningError", "KompasOperationError", "ParamStore", "ParamError",
]
