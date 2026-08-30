"""
Эскиз API5: BeginEdit → ksCircle / ksLineSeg / ksArc* → EndEdit.

ksArcByPoint в КОМПАС: (x1,y1, x2,y2, x3,y3, direction, style) — direction обязателен.
ksArcByAngle: (xc,yc, rad, ang1, ang2, direction, style).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, List, Sequence, Tuple

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part


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
        doc2d = self._ensure()
        r = doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y2), int(style))
        if r == 0:
            raise KompasOperationError("ksLineSeg=0")

    def _ks_arc_angle(
        self,
        xc: float,
        yc: float,
        radius: float,
        ang1_deg: float,
        ang2_deg: float,
        direction: int = 1,
        style: int = 1,
    ) -> bool:
        """True если дуга создана. direction: 1 CCW, -1 CW (как в SDK)."""
        doc2d = self._ensure()
        for name in ("ksArcByAngle", "ksArc"):
            fn = getattr(doc2d, name, None)
            if not callable(fn):
                continue
            for args in (
                (xc, yc, radius, ang1_deg, ang2_deg, direction, style),
                (xc, yc, radius, ang1_deg, ang2_deg, style),
            ):
                try:
                    r = fn(*[float(a) if not isinstance(a, int) else int(a) for a in args])
                    if r != 0:
                        return True
                except Exception:
                    continue
        return False

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
        """Дуга по 3 точкам. direction — обязательный параметр COM."""
        doc2d = self._ensure()
        last_err = None
        for direction in (1, -1):
            for name in ("ksArcByPoint", "ksArc"):
                fn = getattr(doc2d, name, None)
                if not callable(fn):
                    continue
                # полный набор SDK
                for args in (
                    (x1, y1, x2, y2, x3, y3, direction, style),
                    (x1, y1, x2, y2, x3, y3, style),
                ):
                    try:
                        r = fn(
                            *[float(a) if i < 6 else int(a) for i, a in enumerate(args)]
                        )
                        if r != 0:
                            return
                    except Exception as e:
                        last_err = e
                        continue
        raise KompasOperationError(
            f"ksArcByPoint: параметр/вызов. last={last_err}"
        )

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        if radius <= 0:
            raise KompasOperationError(f"circle: radius > 0, got {radius}")
        was = self._editing
        doc2d = self._ensure()
        try:
            result = doc2d.ksCircle(float(xc), float(yc), float(radius), int(style))
            if result == 0:
                raise KompasOperationError("ksCircle=0")
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
        was = self._editing
        try:
            self._ks_arc_3pt(x1, y1, x2, y2, x3, y3, style)
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
        """
        Скруглённый прямоугольник: прямые + четверти окружности.

        Example:
            sk.rounded_rect(-58, -40, 116, 80, radius=40)
        """
        if width <= 0 or height <= 0:
            raise KompasOperationError("rounded_rect: width/height > 0")
        r = min(float(radius), abs(width) / 2.0, abs(height) / 2.0)
        if r <= 1e-9:
            return self.rectangle(x, y, width, height, style=style)

        was = self._editing
        self._ensure()
        try:
            x1, y1 = float(x), float(y)
            x2, y2 = x1 + float(width), y1 + float(height)

            # прямые
            self._ks_line(x1 + r, y1, x2 - r, y1, style)  # bottom
            self._ks_line(x2, y1 + r, x2, y2 - r, style)  # right
            self._ks_line(x2 - r, y2, x1 + r, y2, style)  # top
            self._ks_line(x1, y2 - r, x1, y1 + r, style)  # left

            # углы: центр + углы в градусах (CCW direction=1)
            # bottom-right: center (x2-r, y1+r), from -90° to 0°
            corners = [
                (x2 - r, y1 + r, -90.0, 0.0),  # BR
                (x2 - r, y2 - r, 0.0, 90.0),  # TR
                (x1 + r, y2 - r, 90.0, 180.0),  # TL
                (x1 + r, y1 + r, 180.0, 270.0),  # BL
            ]
            for xc, yc, a1, a2 in corners:
                ok = self._ks_arc_angle(xc, yc, r, a1, a2, direction=1, style=style)
                if not ok:
                    # fallback: 3 точки на четверти
                    def pt(ang_deg: float) -> Tuple[float, float]:
                        rad = math.radians(ang_deg)
                        return (xc + r * math.cos(rad), yc + r * math.sin(rad))

                    p1 = pt(a1)
                    p2 = pt((a1 + a2) / 2.0)
                    p3 = pt(a2)
                    self._ks_arc_3pt(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1], style)
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
        """Овал: R = width/2."""
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
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                self._ks_line(x1, y1, x2, y2, style)
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
        if length < 1e-9 or width <= 0:
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
            mid2 = (x2 + ux * hw, y2 + uy * hw)
            self._ks_arc_3pt(a2[0], a2[1], mid2[0], mid2[1], b2[0], b2[1], style)
            self._ks_line(b2[0], b2[1], b1[0], b1[1], style)
            mid1 = (x1 - ux * hw, y1 - uy * hw)
            self._ks_arc_3pt(b1[0], b1[1], mid1[0], mid1[1], a1[0], a1[1], style)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"slot: {e}") from e
        self._auto_end(was)
        return self
