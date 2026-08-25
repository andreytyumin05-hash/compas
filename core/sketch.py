"""
Эскиз API5: BeginEdit → ksCircle / ksLineSeg / ksArc → EndEdit.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, List, Tuple

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
        """Дуга по трём точкам (start, middle, end) — ksArcByPoint если есть."""
        was = self._editing
        doc2d = self._ensure()
        try:
            if hasattr(doc2d, "ksArcByPoint"):
                r = doc2d.ksArcByPoint(
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2),
                    float(x3),
                    float(y3),
                    int(style),
                )
            elif hasattr(doc2d, "ksArc"):
                r = doc2d.ksArc(
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2),
                    float(x3),
                    float(y3),
                    int(style),
                )
            else:
                # fallback: ломаная из сегментов
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
        pts = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
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

    def slot(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: float,
        style: int = 1,
    ) -> "Sketch":
        """
        Прямой паз (олимпийский): ось от (x1,y1) до (x2,y2), ширина width.
        Аппроксимация многоугольником (надёжнее, чем дуги на всех версиях).
        """
        dx, dy = float(x2) - float(x1), float(y2) - float(y1)
        length = math.hypot(dx, dy)
        if length < 1e-9:
            raise KompasOperationError("slot: нулевая длина")
        ux, uy = dx / length, dy / length
        # перпендикуляр
        px, py = -uy, ux
        hw = float(width) / 2.0
        # прямоугольная часть + полукруги как полигон
        n_cap = 8
        pts: List[Tuple[float, float]] = []

        # сторона +
        pts.append((x1 + px * hw, y1 + py * hw))
        pts.append((x2 + px * hw, y2 + py * hw))
        # полукруг у конца 2
        for i in range(1, n_cap):
            ang = -math.pi / 2 + math.pi * i / n_cap
            # local: along u, perp p
            ca, sa = math.cos(ang), math.sin(ang)
            pts.append((x2 + ux * (sa * hw) + px * (ca * hw), y2 + uy * (sa * hw) + py * (ca * hw)))
        pts.append((x2 - px * hw, y2 - py * hw))
        pts.append((x1 - px * hw, y1 - py * hw))
        for i in range(1, n_cap):
            ang = math.pi / 2 + math.pi * i / n_cap
            ca, sa = math.cos(ang), math.sin(ang)
            pts.append((x1 + ux * (sa * hw) + px * (ca * hw), y1 + uy * (sa * hw) + py * (ca * hw)))

        return self.polygon(pts, closed=True, style=style)
