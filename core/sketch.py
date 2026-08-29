"""
Эскиз API5: BeginEdit → ksCircle / ksLineSeg / ksArc → EndEdit.
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
            raise KompasOperationError(f"BeginEdit эскиза: {e}") from e
        if self._doc2d is None:
            raise KompasOperationError("BeginEdit вернул None")
        self._editing = True
        return self

    def end(self) -> "Sketch":
        if not self._editing:
            return self
        try:
            self._definition.EndEdit
        except Exception as e:
            raise KompasOperationError(f"EndEdit эскиза: {e}") from e
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

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        """Окружность. radius > 0. Example: sk.circle(0, 0, 20)"""
        if radius <= 0:
            raise KompasOperationError(f"circle: radius > 0, получено {radius}")
        was = self._editing
        doc2d = self._ensure()
        try:
            result = doc2d.ksCircle(float(xc), float(yc), float(radius), int(style))
            if result == 0:
                raise KompasOperationError("ksCircle вернул 0 (ошибка)")
        except KompasOperationError:
            self._auto_end(was)
            raise
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"ksCircle: {e}") from e
        self._auto_end(was)
        return self

    def line(self, x1: float, y1: float, x2: float, y2: float, style: int = 1) -> "Sketch":
        """Отрезок. Example: sk.line(0, 0, 50, 0)"""
        was = self._editing
        doc2d = self._ensure()
        try:
            result = doc2d.ksLineSeg(
                float(x1), float(y1), float(x2), float(y2), int(style)
            )
            if result == 0:
                raise KompasOperationError("ksLineSeg вернул 0")
        except KompasOperationError:
            self._auto_end(was)
            raise
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"ksLineSeg: {e}") from e
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
        """Дуга по трём точкам (start, middle, end)."""
        was = self._editing
        doc2d = self._ensure()
        try:
            if hasattr(doc2d, "ksArcByPoint"):
                r = doc2d.ksArcByPoint(
                    float(x1), float(y1), float(x2), float(y2),
                    float(x3), float(y3), int(style),
                )
            elif hasattr(doc2d, "ksArc"):
                r = doc2d.ksArc(
                    float(x1), float(y1), float(x2), float(y2),
                    float(x3), float(y3), int(style),
                )
            else:
                self.line(x1, y1, x2, y2, style=style)
                self.line(x2, y2, x3, y3, style=style)
                self._auto_end(was)
                return self
            if r == 0:
                raise KompasOperationError("ksArc вернул 0")
        except KompasOperationError:
            self._auto_end(was)
            raise
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"arc: {e}") from e
        self._auto_end(was)
        return self

    def rectangle(
        self, x: float, y: float, width: float, height: float, style: int = 1
    ) -> "Sketch":
        """Прямоугольник от левого нижнего угла. Example: sk.rectangle(0, 0, 100, 60)"""
        if width == 0 or height == 0:
            raise KompasOperationError("rectangle: width и height не должны быть 0")
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
        segments: int = 6,
    ) -> "Sketch":
        """
        Скруглённый прямоугольник (аппроксимация полигоном).

        Example:
            sk.rounded_rect(0, 0, 80, 50, radius=5)
        """
        if width <= 0 or height <= 0:
            raise KompasOperationError("rounded_rect: width/height > 0")
        r = min(float(radius), abs(width) / 2, abs(height) / 2)
        if r <= 0:
            return self.rectangle(x, y, width, height, style=style)

        pts: List[Tuple[float, float]] = []
        # corners: BL, BR, TR, TL — quarter circles
        corners = [
            (x + r, y + r, math.pi, 1.5 * math.pi),  # BL
            (x + width - r, y + r, 1.5 * math.pi, 2 * math.pi),  # BR
            (x + width - r, y + height - r, 0, 0.5 * math.pi),  # TR
            (x + r, y + height - r, 0.5 * math.pi, math.pi),  # TL
        ]
        for cx, cy, a0, a1 in corners:
            for i in range(segments + 1):
                t = a0 + (a1 - a0) * i / segments
                pts.append((cx + r * math.cos(t), cy + r * math.sin(t)))
        return self.polygon(pts, closed=True, style=style)

    def ellipse(
        self,
        xc: float,
        yc: float,
        rx: float,
        ry: float,
        style: int = 1,
        segments: int = 48,
    ) -> "Sketch":
        """
        Эллипс (полигон-аппроксимация — совместимо без ksEllipse).

        Example:
            sk.ellipse(0, 0, 40, 25)
        """
        if rx <= 0 or ry <= 0:
            raise KompasOperationError("ellipse: rx и ry > 0")
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
            raise KompasOperationError("Нужно >= 2 точек")
        was = self._editing
        self._ensure()
        try:
            n = len(points)
            count = n if closed else n - 1
            for i in range(count):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                doc2d = self._doc2d
                r = doc2d.ksLineSeg(
                    float(x1), float(y1), float(x2), float(y2), int(style)
                )
                if r == 0:
                    raise KompasOperationError("ksLineSeg вернул 0 в polygon")
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
        """
        Сплайн по опорным точкам — ломаная (надёжный fallback без ksBezier).

        Example:
            sk.spline([(0,0), (10,5), (20,0), (30,8)], closed=False)
        """
        if len(points) < 2:
            raise KompasOperationError("spline: нужно >= 2 точек")
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
        """Прямой паз (олимпийский) ось (x1,y1)-(x2,y2), ширина width."""
        dx, dy = float(x2) - float(x1), float(y2) - float(y1)
        length = math.hypot(dx, dy)
        if length < 1e-9:
            raise KompasOperationError("slot: нулевая длина")
        if width <= 0:
            raise KompasOperationError("slot: width > 0")
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        hw = float(width) / 2.0
        n_cap = 8
        pts: List[Tuple[float, float]] = []
        pts.append((x1 + px * hw, y1 + py * hw))
        pts.append((x2 + px * hw, y2 + py * hw))
        for i in range(1, n_cap):
            ang = -math.pi / 2 + math.pi * i / n_cap
            ca, sa = math.cos(ang), math.sin(ang)
            pts.append(
                (
                    x2 + ux * (sa * hw) + px * (ca * hw),
                    y2 + uy * (sa * hw) + py * (ca * hw),
                )
            )
        pts.append((x2 - px * hw, y2 - py * hw))
        pts.append((x1 - px * hw, y1 - py * hw))
        for i in range(1, n_cap):
            ang = math.pi / 2 + math.pi * i / n_cap
            ca, sa = math.cos(ang), math.sin(ang)
            pts.append(
                (
                    x1 + ux * (sa * hw) + px * (ca * hw),
                    y1 + uy * (sa * hw) + py * (ca * hw),
                )
            )
        return self.polygon(pts, closed=True, style=style)
