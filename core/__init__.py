"""Обёртка КОМПАС-3D (API5)."""

from .connection import KompasApp, get_app
from .part import Part
from .sketch import Sketch
from .exceptions import KompasError, KompasNotRunningError
from .part_fluent import FluentMixin

# Нельзя делать Part.__bases__ = (FluentMixin,) + ... на CPython/Windows:
# TypeError: __bases__ assignment: 'FluentMixin' deallocator differs from 'object'
# Копируем методы на класс — бот и agent импортируют core без падения.
for _name in (
    "var",
    "set_properties",
    "get_context",
    "set_view",
    "screenshot",
    "verify",
):
    if not hasattr(Part, _name) and hasattr(FluentMixin, _name):
        setattr(Part, _name, getattr(FluentMixin, _name))

_orig_init = Part.__init__


def _fluent_init(self, *args, **kwargs):
    _orig_init(self, *args, **kwargs)
    if not hasattr(self, "_fluent_ctx") or getattr(self, "_fluent_ctx", None) is None:
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

__version__ = "0.3.1-visual-fluent"
