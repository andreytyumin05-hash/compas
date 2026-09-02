"""Обёртка КОМПАС-3D (API5)."""

from .connection import KompasApp, get_app
from .part import Part
from .sketch import Sketch
from .exceptions import KompasError, KompasNotRunningError, KompasOperationError
from .params import ParamStore, ParamError, sync_kompas_variable
from .sketch_spline import apply_spline_patch

# Install the real API5 Bezier implementation while keeping the existing
# Sketch.spline()/Sketch.bezier() public API stable.
apply_spline_patch()


def _ensure_params(self) -> ParamStore:
    store = getattr(self, "_params", None)
    if store is None:
        store = ParamStore()
        self._params = store
    return store


def param(self, name: str, value=None, *, expr: str | None = None, note: str = ""):
    """Define a named parameter and try to mirror it into KOMPAS variables.

    Expressions are evaluated by the local deterministic store.  A real KOMPAS
    model variable is created when the running API5 exposes VariableCollection.
    """
    store = _ensure_params(self)
    store.set(name, value, expr=expr)
    try:
        evaluated = store.eval(name)
    except ParamError:
        # Expression can reference a later parameter; defer KOMPAS binding.
        return self
    sync_kompas_variable(self, name, evaluated, note=note)
    return self


def p(self, name: str) -> float:
    return _ensure_params(self).eval(name)


def params_dict(self):
    return _ensure_params(self).eval_all()


def param_graph(self):
    return _ensure_params(self).dependency_graph()


Part.param = param  # type: ignore[attr-defined]
Part.p = p  # type: ignore[attr-defined]
Part.params_dict = params_dict  # type: ignore[attr-defined]
Part.param_graph = param_graph  # type: ignore[attr-defined]


def _no_sketch_on_face(
    self,
    face: str = "top",
    plane: str = "xy",
    *,
    offset: float = 0.0,
):
    raise KompasOperationError(
        "sketch_on_face: выбор реальной грани тела не реализован. "
        "Используйте part.sketch('xy'|'xz'|'yz')."
    )


def _no_shell(
    self,
    thickness: float,
    *,
    faces=None,
    remove_top: bool = True,
):
    raise KompasOperationError("shell: не реализовано в core")


def _no_thread(
    self,
    x: float,
    y: float,
    diameter: float,
    pitch: float,
    length: float,
    *,
    through_all: bool = True,
    plane: str = "xy",
):
    raise KompasOperationError("thread: не реализовано в core")


# Prevent stale fallback implementations from silently producing fake success.
Part.sketch_on_face = _no_sketch_on_face  # type: ignore[attr-defined]
Part.shell = _no_shell  # type: ignore[attr-defined]
Part.thread = _no_thread  # type: ignore[attr-defined]

__all__ = [
    "KompasApp",
    "get_app",
    "Part",
    "Sketch",
    "KompasError",
    "KompasNotRunningError",
    "KompasOperationError",
    "ParamStore",
    "ParamError",
]
