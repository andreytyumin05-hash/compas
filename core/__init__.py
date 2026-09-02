"""Обёртка КОМПАС-3D (API5)."""

from .connection import KompasApp, get_app
from .part import Part
from .sketch import Sketch
from .exceptions import KompasError, KompasNotRunningError, KompasOperationError


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

__all__ = [
    "KompasApp",
    "get_app",
    "Part",
    "Sketch",
    "KompasError",
    "KompasNotRunningError",
]

__version__ = "0.2.1-audit"
