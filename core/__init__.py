"""Обёртка КОМПАС-3D (API5)."""

from .connection import KompasApp, get_app
from .part import Part
from .sketch import Sketch
from .exceptions import KompasError, KompasNotRunningError, KompasOperationError
from .params import ParamStore, ParamError


def _no_sketch_on_face(self, face: str = "top", plane: str = "xy", *, offset: float = 0.0):
    raise KompasOperationError(
        "sketch_on_face: выбор грани тела не реализован. Используйте part.sketch('xy'|'xz'|'yz')."
    )


def _no_shell(self, thickness: float, *, faces=None, remove_top: bool = True):
    raise KompasOperationError(
        "shell: не реализовано в core. Не используйте в сгенерированном коде."
    )


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
    raise KompasOperationError(
        "thread: не реализовано в core. Не используйте в сгенерированном коде."
    )


Part.sketch_on_face = _no_sketch_on_face  # type: ignore
Part.shell = _no_shell  # type: ignore
Part.thread = _no_thread  # type: ignore


def _ensure_params(self):
    if not hasattr(self, "_params") or self._params is None:
        self._params = ParamStore()
    return self._params


def param(self, name: str, value=None, *, expr: str | None = None):
    """Именованный параметр. expr: 'D/2', 'W - 10'."""
    store = _ensure_params(self)
    store.set(name, value, expr=expr)
    return self


def p(self, name: str) -> float:
    return _ensure_params(self).eval(name)


def params_dict(self):
    return _ensure_params(self).eval_all()


def param_graph(self):
    return _ensure_params(self).dependency_graph()


Part.param = param  # type: ignore
Part.p = p  # type: ignore
Part.params_dict = params_dict  # type: ignore
Part.param_graph = param_graph  # type: ignore

__all__ = [
    "KompasApp",
    "get_app",
    "Part",
    "Sketch",
    "KompasError",
    "KompasNotRunningError",
    "ParamStore",
    "ParamError",
]

__version__ = "0.3.0-parametric"
