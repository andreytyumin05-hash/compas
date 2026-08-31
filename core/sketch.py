"""
Эскиз API5 КОМПАС v23 (Codex + smoke на живом COM).

- BeginEdit / EndEdit — property.
- Успех COM: ненулевой int (не 0).
- Дуги: ksArcByAngle(xc, yc, r, ang1, ang2, direction, style).
- ksArcByPoint на v23 не использовать.
- Stadium: не строить нулевые ksLineSeg.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, List, Sequence, Tuple

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

_EPS = 1e-6


def _com_ok(result: Any) -> bool:
    if result is None or result is False:
        return False
    if result is True:
        return True
    try:
        return int(result) != 0
    except Exception:
        return result is not None


class Sketch:
    def __init__(
        self,
        part: "Part",
        entity: Any,
        definition: Any,
        plane_name: str = "xy",
    ):
        self._part = part
        self._entity = entity
        self._definition = definition
        self._plane_name = plane_name
        self._editing = False
        self._doc2d: Any = None

    @property
    def entity(self) -> Any:
        return self._entity

    @property
    def plane_name(self) -> str:
        return self._plane_name

    def begin(self) -> "Sketch":
        if self._editing:
            return self
        try:
            self._doc2d = self._definition.BeginEdit
        except Exception as e:
            raise KompasOperationError(f"BeginEdit: {e}") from e
        if self._doc2d is None:
            raise KompasOperationError("BeginEdit None")
        self._editing = True
        return self

    def end(self) -> "Sketch":
        if not self._editing:
            return self
        try:
            self._definition.EndEdit
        except Exception as e:
            raise KompasOperationError(f"EndEdit: {e}") from e
        finally:
            self._editing = False
            self._doc2d = None
        try:
            self._entity.Update
        except Exception:
            pass
        return self

    def __enter__(self) -> "Sketch":
        return self.begin()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.end()

    def _ensure(self) -> Any:
        if not self._editing:
            self.begin()
        return self._doc2d

    def _auto_end(self, was: bool) -> None:
        if not was and self._editing:
            self.end()

    def _ks_line(self, x1: float, y1: float, x2: float, y2: float, style: int = 1) -> None:
        if abs(float(x2) - float(x1)) < _EPS and abs(float(y2) - float(y1)) < _EPS:
            return
        doc2d = self._ensure()
        r = doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y2), int(style))
        if not _com_ok(r):
            raise KompasOperationError(f"ksLineSeg failed result={r!r}")

    def _ks_arc_angle(
        self,
        xc: float,
        yc: float,
        radius: float,
        ang1_deg: float,
        ang2_deg: float,
        direction: int = 1,
        style: int = 1,
    ) -> None:
        doc2d = self._ensure()
        fn = getattr(doc2d, "ksArcByAngle", None)
        if not callable(fn):
            raise KompasOperationError("ksArcByAngle отсутствует")
        last_err = None
        for d in (int(direction), -int(direction), 1, -1):
            try:
                r = fn(
                    float(xc),
                    float(yc),
                    float(radius),
                    float(ang1_deg),
                    float(ang2_deg),
                    int(d),
                    int(style),
                )
                if _com_ok(r):
                    return
                last_err = f"result={r!r}"
            except Exception as e:
                last_err = e
        raise KompasOperationError(f"ksArcByAngle: {last_err}")

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        if radius <= 0:
            raise KompasOperationError(f"circle: radius > 0, got {radius}")
        was = self._editing
        doc2d = self._ensure()
        try:
            result = doc2d.ksCircle(float(xc), float(yc), float(radius), int(style))
            if not _com_ok(result):
                raise KompasOperationError(f"ksCircle failed result={result!r}")
        except KompasOperationError:
            self._auto_end(was)
            raise
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"ksCircle: {e}") from e
        self._auto_end(was)
        return self

    def line(self, x1: float, y1: float, x2: float, y2: float, style: int = 1) -> "Sketch":
        was = self._editing
        try:
            self._ks_line(x1, y1, x2, y2, style)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"line: {e}") from e
        self._auto_end(was)
        return self

    def arc(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        style: int = 1,
    ) -> "Sketch":
        ax, ay, bx, by, cx, cy = map(float, (x1, y1, x2, y2, x3, y3))
        d = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(d) < _EPS:
            raise KompasOperationError("arc: точки коллинеарны")
        ux = (
            (ax * ax + ay * ay) * (by - cy)
            + (bx * bx + by * by) * (cy - ay)
            + (cx * cx + cy * cy) * (ay - by)
        ) / d
        uy = (
            (ax * ax + ay * ay) * (cx - bx)
            + (bx * bx + by * by) * (ax - cx)
            + (cx * cx + cy * cy) * (bx - ax)
        ) / d
        rad = math.hypot(ax - ux, ay - uy)
        a1 = math.degrees(math.atan2(ay - uy, ax - ux))
        a3 = math.degrees(math.atan2(cy - uy, cx - ux))
        was = self._editing
        try:
            self._ks_arc_angle(ux, uy, rad, a1, a3, direction=1, style=style)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"arc: {e}") from e
        self._auto_end(was)
        return self

    def rectangle(
        self, x: float, y: float, width: float, height: float, style: int = 1
    ) -> "Sketch":
        if width == 0 or height == 0:
            raise KompasOperationError("rectangle: width/height ≠ 0")
        pts = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        ]
        return self.polygon(pts, closed=True, style=style)

    def rounded_rect(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        radius: float,
        style: int = 1,
    ) -> "Sketch":
        """Прямые + четверти ksArcByAngle. Нулевые отрезки пропускаются."""
        if width <= 0 or height <= 0:
            raise KompasOperationError("rounded_rect: width/height > 0")
        r = min(float(radius), abs(width) / 2.0, abs(height) / 2.0)
        if r <= _EPS:
            return self.rectangle(x, y, width, height, style=style)

        was = self._editing
        self._ensure()
        try:
            x1, y1 = float(x), float(y)
            x2, y2 = x1 + float(width), y1 + float(height)

            self._ks_line(x1 + r, y1, x2 - r, y1, style)
            self._ks_line(x2, y1 + r, x2, y2 - r, style)
            self._ks_line(x2 - r, y2, x1 + r, y2, style)
            self._ks_line(x1, y2 - r, x1, y1 + r, style)

            for xc, yc, a1, a2 in (
                (x2 - r, y1 + r, -90.0, 0.0),
                (x2 - r, y2 - r, 0.0, 90.0),
                (x1 + r, y2 - r, 90.0, 180.0),
                (x1 + r, y1 + r, 180.0, 270.0),
            ):
                self._ks_arc_angle(xc, yc, r, a1, a2, direction=1, style=style)
        except KompasOperationError:
            self._auto_end(was)
            raise
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"rounded_rect: {e}") from e
        self._auto_end(was)
        return self

    def stadium(
        self,
        x: float,
        y: float,
        length: float,
        width: float,
        style: int = 1,
    ) -> "Sketch":
        return self.rounded_rect(x, y, length, width, radius=width / 2.0, style=style)

    def ellipse(
        self,
        xc: float,
        yc: float,
        rx: float,
        ry: float,
        style: int = 1,
        segments: int = 48,
    ) -> "Sketch":
        if rx <= 0 or ry <= 0:
            raise KompasOperationError("ellipse: rx, ry > 0")
        pts = [
            (
                xc + rx * math.cos(2 * math.pi * i / segments),
                yc + ry * math.sin(2 * math.pi * i / segments),
            )
            for i in range(segments)
        ]
        return self.polygon(pts, closed=True, style=style)

    def polygon(
        self,
        points: List[Tuple[float, float]],
        closed: bool = True,
        style: int = 1,
    ) -> "Sketch":
        if len(points) < 2:
            raise KompasOperationError(">= 2 точек")
        was = self._editing
        self._ensure()
        try:
            n = len(points)
            count = n if closed else n - 1
            for i in range(count):
                xa, ya = points[i]
                xb, yb = points[(i + 1) % n]
                self._ks_line(xa, ya, xb, yb, style)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"polygon: {e}") from e
        self._auto_end(was)
        return self

    def polyline(
        self,
        points: Sequence[Tuple[float, float]],
        *,
        close: bool = False,
        style: int = 1,
    ) -> "Sketch":
        if len(points) < 2:
            raise KompasOperationError("polyline: >= 2 точки")
        return self.polygon(list(points), closed=close, style=style)

    def arc_by_points(
        self,
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        style: int = 1,
    ) -> "Sketch":
        return self.arc(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], style=style)

    def spline(
        self,
        points: Sequence[Tuple[float, float]],
        closed: bool = False,
        style: int = 1,
    ) -> "Sketch":
        return self.polyline(list(points), close=closed, style=style)

    def bezier(
        self,
        points: Sequence[Tuple[float, float]],
        *,
        closed: bool = False,
        style: int = 1,
    ) -> "Sketch":
        return self.spline(points, closed=closed, style=style)

    def slot(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: float,
        style: int = 1,
    ) -> "Sketch":
        dx, dy = float(x2) - float(x1), float(y2) - float(y1)
        length = math.hypot(dx, dy)
        if length < _EPS or width <= 0:
            raise KompasOperationError("slot: длина/width")
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        hw = float(width) / 2.0
        was = self._editing
        self._ensure()
        try:
            a1 = (x1 + px * hw, y1 + py * hw)
            a2 = (x2 + px * hw, y2 + py * hw)
            b2 = (x2 - px * hw, y2 - py * hw)
            b1 = (x1 - px * hw, y1 - py * hw)
            self._ks_line(a1[0], a1[1], a2[0], a2[1], style)
            ang = math.degrees(math.atan2(uy, ux))
            self._ks_arc_angle(x2, y2, hw, ang - 90, ang + 90, direction=1, style=style)
            self._ks_line(b2[0], b2[1], b1[0], b1[1], style)
            self._ks_arc_angle(x1, y1, hw, ang + 90, ang + 270, direction=1, style=style)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"slot: {e}") from e
        self._auto_end(was)
        return self

    def dim_linear(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        text_x: float | None = None,
        text_y: float | None = None,
    ) -> bool:
        """Линейный размер (best-effort). False = API не принял, геометрия цела."""
        from .sketch_dims import linear_dimension

        was = self._editing
        self._ensure()
        try:
            return bool(
                linear_dimension(
                    self, x1, y1, x2, y2, text_x=text_x, text_y=text_y
                )
            )
        finally:
            self._auto_end(was)

    def dim_radial(
        self,
        xc: float,
        yc: float,
        radius: float,
        *,
        text_x: float | None = None,
        text_y: float | None = None,
    ) -> bool:
        """Радиальный размер окружности (best-effort)."""
        from .sketch_dims import radial_dimension

        was = self._editing
        self._ensure()
        try:
            return bool(
                radial_dimension(
                    self, xc, yc, radius, text_x=text_x, text_y=text_y
                )
            )
        finally:
            self._auto_end(was)

    def dim_rect(self, x: float, y: float, w: float, h: float) -> bool:
        from .sketch_dims import try_auto_dim_rect

        was = self._editing
        self._ensure()
        try:
            return bool(try_auto_dim_rect(self, x, y, w, h))
        finally:
            self._auto_end(was)
