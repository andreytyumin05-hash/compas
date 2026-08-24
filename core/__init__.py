"""
Высокоуровневая обёртка над COM API КОМПАС-3D.

Основная точка входа — класс Part.
"""

from .connection import KompasApp, get_app
from .part import Part
from .sketch import Sketch
from .exceptions import KompasError, KompasNotRunningError

__all__ = [
    "KompasApp",
    "get_app",
    "Part",
    "Sketch",
    "KompasError",
    "KompasNotRunningError",
]

__version__ = "0.1.0"
