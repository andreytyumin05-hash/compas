"""
Эскиз API5: BeginEdit → ksCircle / ksLineSeg / ksArc → EndEdit.

rounded_rect — линии + дуги (не полигон), иначе в КОМПАС «скругления» выглядят как ломаная.
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

    def _ks_line(self, x1: float, y1: float, x2: float, y2: float, style: int = 1) -> None:
        doc2d = self._ensure()
        r = doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y2), int(style))
        if r == 0:
            raise KompasOperationError("ksLineSeg вернул 0")

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
        """Дуга по 3 точкам (начало, промежуточная, конец)."""
        doc2d = self._ensure()
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
            # крайний fallback — короткие сегменты только для этой дуги
            self._ks_line(x1, y1, x2, y2, style)
            self._ks_line(x2, y2, x3, y3, style)
            return
        if r == 0:
            raise KompasOperationError("ksArc вернул 0")

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        if radius <= 0:
            raise KompasOperationError(f"circle: radius > 0, получено {radius}")
        was = self._editing
        doc2d = self._ensure()
        try:
            result = doc2d.ksCircle(float(xc), float(yc), float(radius), int(style))
            if result == 0:
                raise KompasOperationError("ksCircle вернул 0")
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
        Скруглённый прямоугольник: прямые + четверти окружности (ksArc).

        x,y — левый нижний угол; width/height > 0; radius ограничен половиной меньшей стороны.

        Example:
            sk.rounded_rect(-58, -40, 116, 80, radius=40)  # stadium 116×80
        """
        if width <= 0 or height <= 0:
            raise KompasOperationError("rounded_rect: width и height > 0")
        r = float(radius)
        r = min(r, abs(width) / 2.0, abs(height) / 2.0)
        if r <= 1e-9:
            return self.rectangle(x, y, width, height, style=style)

        # stadium: радиус = половина меньшей стороны → два полукруга + две прямые
        was = self._editing
        self._ensure()
        try:
            x1, y1 = float(x), float(y)
            x2, y2 = x1 + float(width), y1 + float(height)

            # Нижняя прямая
            self._ks_line(x1 + r, y1, x2 - r, y1, style)
            # Нижний правый угол: центр (x2-r, y1+r), от юга к востоку
            self._ks_arc_3pt(
                x2 - r, y1,
                x2 - r + r * math.cos(math.radians(-45)), y1 + r + r * math.sin(math.radians(-45)),
                x2, y1 + r,
                style,
            )
            # Правая прямая
            self._ks_line(x2, y1 + r, x2, y2 - r, style)
            # Верхний правый: центр (x2-r, y2-r)
            self._ks_arc_3pt(
                x2, y2 - r,
                x2 - r + r * math.cos(math.radians(45)), y2 - r + r * math.sin(math.radians(45)),
                x2 - r, y2,
                style,
            )
            # Верхняя прямая
            self._ks_line(x2 - r, y2, x1 + r, y2, style)
            # Верхний левый: центр (x1+r, y2-r)
            self._ks_arc_3pt(
                x1 + r, y2,
                x1 + r + r * math.cos(math.radians(135)), y2 - r + r * math.sin(math.radians(135)),
                x1, y2 - r,
                style,
            )
            # Левая прямая
            self._ks_line(x1, y2 - r, x1, y1 + r, style)
            # Нижний левый: центр (x1+r, y1+r)
            self._ks_arc_3pt(
                x1, y1 + r,
                x1 + r + r * math.cos(math.radians(-135)), y1 + r + r * math.sin(math.radians(-135)),
                x1 + r, y1,
                style,
            )
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
        """
        Овал/«стадион»: length вдоль X, width вдоль Y, торцы — полуокружности R=width/2.

        Example:
            sk.stadium(-58, -40, 116, 80)  # то же что rounded_rect(..., radius=40)
        """
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
        if len(points) < 2:
            raise KompasOperationError("spline: >= 2 точек")
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
        """Прямой паз: две прямые + два полукруга (дуги)."""
        dx, dy = float(x2) - float(x1), float(y2) - float(y1)
        length = math.hypot(dx, dy)
        if length < 1e-9:
            raise KompasOperationError("slot: нулевая длина")
        if width <= 0:
            raise KompasOperationError("slot: width > 0")
        ux, uy = dx / length, dy / length
        px, py = -uy, ux
        hw = float(width) / 2.0

        was = self._editing
        self._ensure()
        try:
            # точки
            a1 = (x1 + px * hw, y1 + py * hw)
            a2 = (x2 + px * hw, y2 + py * hw)
            b2 = (x2 - px * hw, y2 - py * hw)
            b1 = (x1 - px * hw, y1 - py * hw)
            # прямые
            self._ks_line(a1[0], a1[1], a2[0], a2[1], style)
            # полукруг у конца 2
            mid2 = (x2 + ux * hw, y2 + uy * hw)  # наружу вдоль оси — лучше перпендикуляр
            mid2 = (x2 + px * 0.0 + ux * 0, y2)  # midpoint of semicircle in +perp direction from center end
            mid2 = (x2 + px * hw * 0 + (x2 + ux * 0), y2)
            # середина дуги на продолжении перпендикуляра через конец
            mid2 = (x2 + px * hw, y2 + py * hw)  # same as a2 — wrong
            mid2 = (x2 + ux * 0 + px * 0, y2) 
            # correct mid of semicircle from a2 to b2 going through (x2+ux*hw? no)
            # from a2 to b2 around center (x2,y2), mid at (x2+ux*hw, y2+uy*hw) if going outward along axis
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
