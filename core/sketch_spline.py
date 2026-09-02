"""Реальный spline через API5 ksBezier + ksPoint + ksEndObj."""

from __future__ import annotations

from typing import Sequence, Tuple

from .exceptions import KompasOperationError


def spline_impl(
    self,
    points: Sequence[Tuple[float, float]],
    closed: bool = False,
    style: int = 1,
):
    pts = list(points)
    if len(pts) < 2:
        raise KompasOperationError("spline: нужно >= 2 точек")
    was = self._editing
    self._ensure()
    doc2d = self._doc2d
    try:
        fn = getattr(doc2d, "ksBezier", None)
        if not callable(fn):
            raise KompasOperationError(
                "spline: ksBezier недоступен в Document2D (проверьте API5 v23)"
            )
        closed_i = 1 if closed else 0
        start = fn(closed_i, int(style))
        if start is False or start == 0:
            raise KompasOperationError(f"ksBezier start failed result={start!r}")
        pt_fn = getattr(doc2d, "ksPoint", None)
        if not callable(pt_fn):
            raise KompasOperationError("spline: ksPoint недоступен")
        for x, y in pts:
            pr = pt_fn(float(x), float(y), 0)
            if pr is False or pr == 0:
                raise KompasOperationError(f"ksPoint({x},{y}) failed result={pr!r}")
        end = getattr(doc2d, "ksEndObj", None)
        if not callable(end):
            raise KompasOperationError("spline: ksEndObj недоступен")
        obj = end()
        if obj is False or obj == 0 or obj is None:
            raise KompasOperationError(f"ksEndObj failed result={obj!r}")
    except KompasOperationError:
        self._auto_end(was)
        raise
    except Exception as e:
        self._auto_end(was)
        raise KompasOperationError(f"spline: {e}") from e
    self._auto_end(was)
    return self


def apply_spline_patch() -> None:
    from .sketch import Sketch

    Sketch.spline = spline_impl  # type: ignore
    Sketch.bezier = lambda self, points, closed=False, style=1: spline_impl(
        self, points, closed=closed, style=style
    )  # type: ignore
