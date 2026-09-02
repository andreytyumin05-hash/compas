"""Real KOMPAS API5 Bezier/spline support.

KOMPAS API5 creates a Bezier object with ksBezier, accepts its points, and
finishes it with ksEndObj.  This module patches Sketch.spline without changing
the public Sketch API used by existing templates.
"""

from __future__ import annotations

from typing import Sequence, Tuple

from .exceptions import KompasOperationError


def spline_impl(
    self,
    points: Sequence[Tuple[float, float]],
    closed: bool = False,
    style: int = 1,
):
    pts = [(float(x), float(y)) for x, y in points]
    if len(pts) < 2:
        raise KompasOperationError("spline: нужно >= 2 точек")
    if any(not __import__("math").isfinite(v) for p in pts for v in p):
        raise KompasOperationError("spline: координаты должны быть конечными")

    was = self._editing
    self._ensure()
    doc2d = self._doc2d
    try:
        bezier = getattr(doc2d, "ksBezier", None)
        point = getattr(doc2d, "ksPoint", None)
        end_obj = getattr(doc2d, "ksEndObj", None)
        if not callable(bezier) or not callable(point) or not callable(end_obj):
            raise KompasOperationError(
                "spline: ksBezier/ksPoint/ksEndObj недоступны в текущем API5"
            )

        result = bezier(1 if closed else 0, int(style))
        if result in (None, False, 0):
            raise KompasOperationError(f"ksBezier failed result={result!r}")

        for x, y in pts:
            result = point(x, y, 0)
            if result in (None, False, 0):
                raise KompasOperationError(
                    f"ksPoint({x:g},{y:g}) failed result={result!r}"
                )

        curve = end_obj()
        if curve in (None, False, 0):
            raise KompasOperationError(f"ksEndObj failed result={curve!r}")
    except KompasOperationError:
        self._auto_end(was)
        raise
    except Exception as exc:
        self._auto_end(was)
        raise KompasOperationError(f"spline: {exc}") from exc

    self._auto_end(was)
    return self


def apply_spline_patch() -> None:
    from .sketch import Sketch

    Sketch.spline = spline_impl  # type: ignore[attr-defined]
    Sketch.bezier = lambda self, points, closed=False, style=1: spline_impl(
        self, points, closed=closed, style=style
    )  # type: ignore[attr-defined]
