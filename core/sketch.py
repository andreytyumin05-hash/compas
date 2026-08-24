"""
Работа с эскизами в КОМПАС-3D.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Tuple

from win32com.client import CastTo

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part


class Sketch:
    """
    Высокоуровневый эскиз.

    После создания геометрии нужно вызвать part._commit_sketch(self)
    или использовать контекстный менеджер / методы Part.
    """

    def __init__(self, part: "Part", sketch_entity: Any, plane_name: str = "xy"):
        self._part = part
        self._entity = sketch_entity
        self._plane_name = plane_name
        self._closed = False
        self._geometry_added = False

    @property
    def entity(self) -> Any:
        return self._entity

    @property
    def plane_name(self) -> str:
        return self._plane_name

    def _ensure_edit(self) -> Any:
        """Открыть эскиз на редактирование и вернуть drawing container."""
        if self._closed:
            raise KompasOperationError("Эскиз уже закрыт")

        fragment = self._entity.BeginEdit()
        view = fragment.ViewsAndLayersManager.Views.View(0)
        drawing = CastTo(view, "IDrawingContainer")
        return drawing

    def _finish_edit(self) -> None:
        self._entity.EndEdit()
        self._entity.Update()

    # ------------------------------------------------------------------
    # Примитивы
    # ------------------------------------------------------------------

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        """
        Окружность.

        style=1 — основная линия (нужна для контура выдавливания).
        """
        drawing = self._ensure_edit()
        try:
            circle = CastTo(drawing.Circles.Add(), "ICircle")
            circle.Xc = float(xc)
            circle.Yc = float(yc)
            circle.Radius = float(radius)
            circle.Style = int(style)
            circle.Update()
            self._geometry_added = True
        finally:
            self._finish_edit()
        return self

    def rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        style: int = 1,
    ) -> "Sketch":
        """Прямоугольник по левому нижнему углу, ширине и высоте."""
        drawing = self._ensure_edit()
        try:
            # Рисуем четырьмя отрезками (универсальнее, чем специфичный Rectangle)
            pts = [
                (x, y),
                (x + width, y),
                (x + width, y + height),
                (x, y + height),
            ]
            for i in range(4):
                x1, y1 = pts[i]
                x2, y2 = pts[(i + 1) % 4]
                line = CastTo(drawing.Lines.Add(), "ILineSegment")
                line.X1, line.Y1 = float(x1), float(y1)
                line.X2, line.Y2 = float(x2), float(y2)
                line.Style = int(style)
                line.Update()
            self._geometry_added = True
        finally:
            self._finish_edit()
        return self

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        style: int = 1,
    ) -> "Sketch":
        """Отрезок."""
        drawing = self._ensure_edit()
        try:
            line = CastTo(drawing.Lines.Add(), "ILineSegment")
            line.X1, line.Y1 = float(x1), float(y1)
            line.X2, line.Y2 = float(x2), float(y2)
            line.Style = int(style)
            line.Update()
            self._geometry_added = True
        finally:
            self._finish_edit()
        return self

    def polygon(
        self,
        points: List[Tuple[float, float]],
        closed: bool = True,
        style: int = 1,
    ) -> "Sketch":
        """Многоугольник по списку точек [(x, y), ...]."""
        if len(points) < 2:
            raise KompasOperationError("Нужно минимум 2 точки")

        drawing = self._ensure_edit()
        try:
            n = len(points)
            count = n if closed else n - 1
            for i in range(count):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                line = CastTo(drawing.Lines.Add(), "ILineSegment")
                line.X1, line.Y1 = float(x1), float(y1)
                line.X2, line.Y2 = float(x2), float(y2)
                line.Style = int(style)
                line.Update()
            self._geometry_added = True
        finally:
            self._finish_edit()
        return self

    def close(self) -> None:
        """Явно закрыть эскиз (обычно не требуется — методы сами закрывают)."""
        self._closed = True
