"""Automatic visible dimensions for common sketch primitives.

Dimensions are created immediately after geometry when COMPAS_AUTO_DIM is enabled
(default). A failed dimension annotation never invalidates otherwise valid geometry.
"""

from __future__ import annotations

import os
from functools import wraps


def _enabled() -> bool:
    value = os.getenv("COMPAS_AUTO_DIM", "1").strip().lower()
    return value not in {"0", "false", "no", "off"}


def apply_auto_dimension_patch() -> None:
    from .sketch import Sketch

    original_circle = Sketch.circle
    original_rectangle = Sketch.rectangle
    original_line = Sketch.line

    @wraps(original_circle)
    def circle(self, xc, yc, radius, style=1):
        result = original_circle(self, xc, yc, radius, style=style)
        if _enabled():
            try:
                from .sketch_dims import radial_dimension
                radial_dimension(self, float(xc), float(yc), float(radius), diameter=True)
            except Exception:
                pass
        return result

    @wraps(original_line)
    def line(self, x1, y1, x2, y2, style=1):
        result = original_line(self, x1, y1, x2, y2, style=style)
        if _enabled() and abs(float(x2) - float(x1)) + abs(float(y2) - float(y1)) > 1e-9:
            try:
                from .sketch_dims import linear_dimension
                linear_dimension(self, float(x1), float(y1), float(x2), float(y2))
            except Exception:
                pass
        return result

    @wraps(original_rectangle)
    def rectangle(self, x, y, width, height, style=1):
        result = original_rectangle(self, x, y, width, height, style=style)
        if _enabled():
            try:
                from .sketch_dims import try_auto_dim_rect
                try_auto_dim_rect(self, float(x), float(y), float(width), float(height))
            except Exception:
                pass
        return result

    Sketch.circle = circle  # type: ignore[attr-defined]
    Sketch.line = line  # type: ignore[attr-defined]
    Sketch.rectangle = rectangle  # type: ignore[attr-defined]
