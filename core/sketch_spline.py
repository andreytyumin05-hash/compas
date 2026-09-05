"""Реальный spline/Bezier через API5 KOMPAS-3D v23."""

from __future__ import annotations

import math
from typing import Any, Sequence, Tuple

from .exceptions import KompasOperationError

KO_BEZIER_POINT_PARAM = 17


def _ok(value: Any) -> bool:
    if value is None or value is False:
        return False
    try:
        return int(value) != 0
    except Exception:
        return True


def _param_value(obj: Any, names: tuple[str, ...], value: Any) -> bool:
    for name in names:
        try:
            setattr(obj, name, value)
            return True
        except Exception:
            continue
    return False


def _handle_data(pts: list[tuple[float, float]], i: int, smooth: bool) -> tuple[float, float, float]:
    """Return handle lengths and tangent angle for a smooth Bezier node."""
    if not smooth:
        return 0.0, 0.0, 0.0
    x, y = pts[i]
    if i == 0:
        nxt = pts[1]
        vx, vy = nxt[0] - x, nxt[1] - y
        return 0.0, math.hypot(vx, vy) * 0.30, math.degrees(math.atan2(vy, vx))
    if i == len(pts) - 1:
        prev = pts[i - 1]
        vx, vy = x - prev[0], y - prev[1]
        return math.hypot(vx, vy) * 0.30, 0.0, math.degrees(math.atan2(vy, vx))
    prev, nxt = pts[i - 1], pts[i + 1]
    vx, vy = nxt[0] - prev[0], nxt[1] - prev[1]
    return (
        math.hypot(x - prev[0], y - prev[1]) * 0.30,
        math.hypot(nxt[0] - x, nxt[1] - y) * 0.30,
        math.degrees(math.atan2(vy, vx)),
    )


def _create_bezier_point(
    doc2d: Any,
    kompas: Any,
    pts: list[tuple[float, float]],
    index: int,
    smooth: bool,
) -> None:
    get_ps = getattr(kompas, "GetParamStruct", None)
    point_fn = getattr(doc2d, "ksBezierPoint", None)
    if not callable(get_ps) or not callable(point_fn):
        raise KompasOperationError("spline: ksBezierPoint/GetParamStruct недоступны в API5")

    param = get_ps(KO_BEZIER_POINT_PARAM)
    if param is None:
        raise KompasOperationError("spline: ksBezierPointParam is None")
    try:
        init = getattr(param, "Init", None)
        if callable(init):
            init()
    except Exception:
        pass

    x, y = pts[index]
    if not _param_value(param, ("x", "X"), float(x)) or not _param_value(param, ("y", "Y"), float(y)):
        raise KompasOperationError("spline: не удалось задать x/y BezierPointParam")

    left_len, right_len, angle = _handle_data(pts, index, smooth)
    _param_value(param, ("left", "Left"), float(left_len))
    _param_value(param, ("right", "Right"), float(right_len))
    _param_value(param, ("ang", "angle", "Angle"), float(angle))

    try:
        result = point_fn(param)
    except Exception as exc:
        raise KompasOperationError(f"ksBezierPoint({index}) failed: {exc}") from exc
    if not _ok(result):
        raise KompasOperationError(f"ksBezierPoint({index}) returned {result!r}")


def spline_impl(
    self,
    points: Sequence[Tuple[float, float]],
    closed: bool = False,
    style: int = 1,
    smooth: bool = True,
):
    pts = [(float(x), float(y)) for x, y in points]
    minimum = 3 if smooth else 2
    if len(pts) < minimum:
        raise KompasOperationError(f"spline: нужно >= {minimum} точек")
    if any(not math.isfinite(v) for p in pts for v in p):
        raise KompasOperationError("spline: координаты должны быть конечными")

    was = self._editing
    self._ensure()
    doc2d = self._doc2d
    try:
        bezier = getattr(doc2d, "ksBezier", None)
        end_obj = getattr(doc2d, "ksEndObj", None)
        if not callable(bezier) or not callable(end_obj):
            raise KompasOperationError("spline: ksBezier/ksEndObj недоступны в текущем API5")

        app = self._part.app
        kompas = getattr(app, "k5", None) or getattr(app, "app7", None)
        if kompas is None or not callable(getattr(kompas, "GetParamStruct", None)):
            raise KompasOperationError("spline: KompasObject.GetParamStruct недоступен")

        result = bezier(1 if closed else 0, int(style))
        if not _ok(result):
            raise KompasOperationError(f"ksBezier failed result={result!r}")

        for i in range(len(pts)):
            _create_bezier_point(doc2d, kompas, pts, i, smooth=smooth)

        curve = end_obj()
        if not _ok(curve):
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
    Sketch.bezier = lambda self, points, closed=False, style=1, smooth=True: spline_impl(
        self, points, closed=closed, style=style, smooth=smooth
    )  # type: ignore[attr-defined]
