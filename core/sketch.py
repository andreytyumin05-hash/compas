"""
Эскиз API5 КОМПАС v23 (проверено на живом COM):

<<<<<<< HEAD
Компас v23: ksLineSeg и ksCircle возвращают число > 0 при успехе, не 0.
ksArcByAngle работает как: (xc, yc, rad, ang1, ang2, direction, style).
ksArcByPoint на этой машине не принимает обязательные параметры и не подходит как fallback.
=======
- BeginEdit / EndEdit — property (без ()).
- ksLineSeg / ksCircle: успех = ненулевой код (часто 0x4000001F), провал = 0 или exception.
- Дуги: только ksArcByAngle(xc, yc, r, ang1, ang2, direction, style).
  ksArcByPoint на v23 падает «Параметр обязательный» — не использовать.
- Stadium (R = width/2): не строить нулевые отрезки (длина 0).
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, List, Sequence, Tuple

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

_EPS = 1e-6


def _com_ok(result: Any) -> bool:
    """v23: успех — ненулевое int; 0 / None — нет."""
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

    @staticmethod
    def _com_success(value: Any) -> bool:
        if value is None:
            return False
        try:
            return int(value) != 0
        except Exception:
            return bool(value)

    def _ks_line(self, x1: float, y1: float, x2: float, y2: float, style: int = 1) -> None:
<<<<<<< HEAD
        if abs(float(x2) - float(x1)) < 1e-9 and abs(float(y2) - float(y1)) < 1e-9:
            return
        doc2d = self._ensure()
        r = doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y2), int(style))
        if not self._com_success(r):
            raise KompasOperationError("ksLineSeg=0")
=======
        if abs(x2 - x1) < _EPS and abs(y2 - y1) < _EPS:
            return  # нулевой сегмент — пропускаем (stadium)
        doc2d = self._ensure()
        r = doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y2), int(style))
        if not _com_ok(r):
            raise KompasOperationError(f"ksLineSeg failed result={r!r}")
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a

    def _ks_arc_angle(
        self,
        xc: float,
        yc: float,
        radius: float,
        ang1_deg: float,
        ang2_deg: float,
        direction: int = 1,
        style: int = 1,
<<<<<<< HEAD
    ) -> bool:
        """True if arc created. On v23 the working signature is ksArcByAngle(..., direction, style)."""
        doc2d = self._ensure()
        for name in ("ksArcByAngle", "ksArc"):
            fn = getattr(doc2d, name, None)
            if not callable(fn):
                continue
            for args in (
                (xc, yc, radius, ang1_deg, ang2_deg, direction, style),
                (xc, yc, radius, ang1_deg, ang2_deg, direction),
                (xc, yc, radius, ang1_deg, ang2_deg, style),
                (xc, yc, radius, ang1_deg, ang2_deg),
            ):
                try:
                    r = fn(*[float(a) if not isinstance(a, int) else int(a) for a in args])
                    if self._com_success(r):
                        return True
                except Exception:
                    continue
        return False

    @staticmethod
    def _norm_angle_deg(angle_deg: float) -> float:
        return float(angle_deg) % 360.0

    @staticmethod
    def _angle_between_ccw(start_deg: float, mid_deg: float, end_deg: float) -> bool:
        s = Sketch._norm_angle_deg(start_deg)
        m = Sketch._norm_angle_deg(mid_deg)
        e = Sketch._norm_angle_deg(end_deg)
        if s <= e:
            return s <= m <= e
        return m >= s or m <= e

    def _ks_arc_3pt(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        x3: float,
        y3: float,
        style: int = 1,
    ) -> None:
        """Fallback for 3-point arcs. On v23 ksArcByPoint is not a valid working form."""
        doc2d = self._ensure()
        last_err: Exception | None = None

        for direction in (1, -1):
            for name in ("ksArcByPoint", "ksArc"):
                fn = getattr(doc2d, name, None)
                if not callable(fn):
                    continue
                for args in ((x1, y1, x2, y2, x3, y3, direction, style), (x1, y1, x2, y2, x3, y3, style)):
                    try:
                        r = fn(*[float(a) if i < 6 else int(a) for i, a in enumerate(args)])
                        if self._com_success(r):
                            return
                    except Exception as e:
                        last_err = e
                        continue

        ax, ay = float(x1), float(y1)
        bx, by = float(x2), float(y2)
        cx, cy = float(x3), float(y3)
        denom = 2.0 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(denom) < 1e-9:
            raise KompasOperationError(f"ksArcByPoint: коллинеарные точки; last={last_err}")

        xc = ((ax * ax + ay * ay) * (by - cy) + (bx * bx + by * by) * (cy - ay) + (cx * cx + cy * cy) * (ay - by)) / denom
        yc = ((ax * ax + ay * ay) * (cx - bx) + (bx * bx + by * by) * (ax - cx) + (cx * cx + cy * cy) * (bx - ax)) / denom
        radius = math.hypot(ax - xc, ay - yc)
        if radius <= 1e-9:
            raise KompasOperationError(f"ksArcByPoint: нулевой радиус; last={last_err}")

        a1 = math.degrees(math.atan2(ay - yc, ax - xc))
        a2 = math.degrees(math.atan2(by - yc, bx - xc))
        a3 = math.degrees(math.atan2(cy - yc, cx - xc))
        ang1 = self._norm_angle_deg(a1)
        ang3 = self._norm_angle_deg(a3)
        mid = self._norm_angle_deg(a2)
        direction = 1 if self._angle_between_ccw(ang1, mid, ang3) else -1
        start, end = (ang1, ang3) if direction == 1 else (ang3, ang1)

        for name in ("ksArcByAngle", "ksArc"):
            fn = getattr(doc2d, name, None)
            if not callable(fn):
                continue
            for args in (
                (xc, yc, radius, start, end, direction, style),
                (xc, yc, radius, start, end, direction),
                (xc, yc, radius, start, end, style),
            ):
                try:
                    r = fn(*[float(a) if not isinstance(a, int) else int(a) for a in args])
                    if self._com_success(r):
                        return
                except Exception as e:
                    last_err = e
                    continue

        raise KompasOperationError(f"ksArcByPoint: параметр/вызов. last={last_err}")
=======
    ) -> None:
        """
        Рабочая сигнатура v23:
          ksArcByAngle(xc, yc, radius, ang1, ang2, direction, style)
        direction: 1 CCW, -1 CW. Углы в градусах.
        """
        doc2d = self._ensure()
        fn = getattr(doc2d, "ksArcByAngle", None)
        if not callable(fn):
            raise KompasOperationError("ksArcByAngle отсутствует на doc2d")
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
                continue
        raise KompasOperationError(f"ksArcByAngle: {last_err}")
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        if radius <= 0:
            raise KompasOperationError(f"circle: radius > 0, got {radius}")
        was = self._editing
        doc2d = self._ensure()
        try:
            result = doc2d.ksCircle(float(xc), float(yc), float(radius), int(style))
<<<<<<< HEAD
            if not self._com_success(result):
                raise KompasOperationError("ksCircle=0")
=======
            if not _com_ok(result):
                raise KompasOperationError(f"ksCircle failed result={result!r}")
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a
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
        """Дуга по 3 точкам → через центр и углы (ksArcByPoint на v23 ненадёжен)."""
        # окружность по 3 точкам
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
        a2 = math.degrees(math.atan2(cy - uy, cx - ux))
        was = self._editing
        try:
            self._ks_arc_angle(ux, uy, rad, a1, a2, direction=1, style=style)
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
<<<<<<< HEAD
        """Rounded rectangle: straight edges + quarter arcs."""
=======
        """
        Прямые (ненулевой длины) + четверти/полуокружности ksArcByAngle.

        Example:
            sk.rounded_rect(-58, -40, 116, 80, radius=40)  # stadium
        """
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a
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

<<<<<<< HEAD
=======
            # прямые — пропускаются если длина ~0 (полный stadium)
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a
            self._ks_line(x1 + r, y1, x2 - r, y1, style)
            self._ks_line(x2, y1 + r, x2, y2 - r, style)
            self._ks_line(x2 - r, y2, x1 + r, y2, style)
            self._ks_line(x1, y2 - r, x1, y1 + r, style)

<<<<<<< HEAD
=======
            # углы: BR, TR, TL, BL (CCW, direction=1)
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a
            corners = [
                (x2 - r, y1 + r, -90.0, 0.0),
                (x2 - r, y2 - r, 0.0, 90.0),
                (x1 + r, y2 - r, 90.0, 180.0),
                (x1 + r, y1 + r, 180.0, 270.0),
            ]
            for xc, yc, a1, a2 in corners:
<<<<<<< HEAD
                ok = self._ks_arc_angle(xc, yc, r, a1, a2, direction=1, style=style)
                if not ok:
                    def pt(ang_deg: float) -> Tuple[float, float]:
                        rad = math.radians(ang_deg)
                        return (xc + r * math.cos(rad), yc + r * math.sin(rad))

                    p1 = pt(a1)
                    p2 = pt((a1 + a2) / 2.0)
                    p3 = pt(a2)
                    self._ks_arc_3pt(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], style)
=======
                self._ks_arc_angle(xc, yc, r, a1, a2, direction=1, style=style)
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a
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
<<<<<<< HEAD
        """Oval: R = width/2."""
=======
>>>>>>> dad1ba3a61020050715cce183fa9389d4057bf0a
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

    def spline(
        self,
        points: Sequence[Tuple[float, float]],
        closed: bool = False,
        style: int = 1,
    ) -> "Sketch":
        return self.polygon(list(points), closed=closed, style=style)

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
            # полукруги через углы относительно оси паза — упрощённо ArcByAngle
            ang = math.degrees(math.atan2(uy, ux))
            self._ks_arc_angle(x2, y2, hw, ang - 90, ang + 90, direction=1, style=style)
            self._ks_line(b2[0], b2[1], b1[0], b1[1], style)
            self._ks_arc_angle(x1, y1, hw, ang + 90, ang + 270, direction=1, style=style)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"slot: {e}") from e
        self._auto_end(was)
        return self
