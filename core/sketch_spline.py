"""Реальный spline/Bezier через API5 KOMPAS-3D v23.

Путь A: ksBezier + ksBezierPoint(GetParamStruct) + ksEndObj
Путь B (форум): ksBezier + ksPoint + ksEndObj
"""

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
    ang = math.degrees(math.atan2(vy, vx))
    d = math.hypot(vx, vy) * 0.25
    return d, d, ang


def _create_bezier_point(doc2d: Any, kompas: Any, pts: list, index: int, smooth: bool) -> None:
    x, y = pts[index]
    left_len, right_len, angle = _handle_data(pts, index, smooth)
    get_ps = getattr(kompas, "GetParamStruct", None)
    if not callable(get_ps):
        raise KompasOperationError("GetParamStruct недоступен для ksBezierPoint")
    try:
        param = get_ps(KO_BEZIER_POINT_PARAM)
    except Exception as exc:
        raise KompasOperationError(f"GetParamStruct(BezierPoint): {exc}") from exc
    if param is None:
        raise KompasOperationError("GetParamStruct(BezierPoint) None")
    _param_value(param, ("x", "X"), float(x))
    _param_value(param, ("y", "Y"), float(y))
    _param_value(param, ("angle", "Angle"), float(angle))
    _param_value(param, ("leftLength", "LeftLength"), float(left_len))
    _param_value(param, ("rightLength", "RightLength"), float(right_len))
    fn = getattr(doc2d, "ksBezierPoint", None)
    if not callable(fn):
        raise KompasOperationError("ksBezierPoint отсутствует")
    try:
        result = fn(param)
    except Exception as exc:
        raise KompasOperationError(f"ksBezierPoint({index}): {exc}") from exc
    if not _ok(result):
        raise KompasOperationError(f"ksBezierPoint({index}) returned {result!r}")


def _fill_points_simple(doc2d: Any, pts: list[tuple[float, float]]) -> None:
    pt_fn = getattr(doc2d, "ksPoint", None)
    if not callable(pt_fn):
        raise KompasOperationError("spline: ksPoint недоступен")
    for x, y in pts:
        pr = pt_fn(float(x), float(y), 0)
        if not _ok(pr):
            raise KompasOperationError(f"ksPoint({x},{y}) failed: {pr!r}")


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
        raise KompasOperationError(f"spline: нужно >= {minimum} точек (smooth={smooth})")
    if any(not math.isfinite(v) for p in pts for v in p):
        raise KompasOperationError("spline: координаты должны быть конечными")

    was = self._editing
    self._ensure()
    doc2d = self._doc2d
    try:
        bezier = getattr(doc2d, "ksBezier", None)
        end_obj = getattr(doc2d, "ksEndObj", None)
        if not callable(bezier) or not callable(end_obj):
            raise KompasOperationError("spline: ksBezier/ksEndObj недоступны в API5")

        app = self._part.app
        kompas = getattr(app, "k5", None) or getattr(app, "app7", None)

        result = bezier(1 if closed else 0, int(style))
        if not _ok(result):
            raise KompasOperationError(f"ksBezier failed result={result!r}")

        path = "bezier_point"
        try:
            if kompas is None or not callable(getattr(kompas, "GetParamStruct", None)):
                raise KompasOperationError("no GetParamStruct")
            for i in range(len(pts)):
                _create_bezier_point(doc2d, kompas, pts, i, smooth=smooth)
        except Exception:
            path = "ksPoint"
            try:
                end_obj()
            except Exception:
                pass
            result = bezier(1 if closed else 0, int(style))
            if not _ok(result):
                raise KompasOperationError(f"ksBezier restart failed: {result!r}")
            _fill_points_simple(doc2d, pts)

        curve = end_obj()
        if not _ok(curve):
            raise KompasOperationError(f"ksEndObj failed path={path} result={curve!r}")
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
