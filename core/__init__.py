"""Обёртка КОМПАС-3D (API5)."""

from .connection import KompasApp, get_app
from .part import Part
from .sketch import Sketch
from .exceptions import KompasError, KompasNotRunningError
from .part_fluent import FluentMixin

# Подмешиваем Visual Fluent, даже если class Part в part.py без наследования
if not issubclass(Part, FluentMixin):
    Part.__bases__ = (FluentMixin,) + Part.__bases__

# контекст по умолчанию
_orig_init = Part.__init__


def _fluent_init(self, *args, **kwargs):
    _orig_init(self, *args, **kwargs)
    if not hasattr(self, "_fluent_ctx") or self._fluent_ctx is None:
        self._fluent_ctx = {}


Part.__init__ = _fluent_init  # type: ignore

__all__ = [
    "KompasApp",
    "get_app",
    "Part",
    "Sketch",
    "KompasError",
    "KompasNotRunningError",
]

__version__ = "0.3.0-visual-fluent"
