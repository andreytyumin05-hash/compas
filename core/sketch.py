"""
Эскизы КОМПАС-3D (late binding, без CastTo/makepy).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Tuple

from .comutil import safe_cast
from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part


class Sketch:
    def __init__(self, part: "Part", sketch_entity: Any, plane_name: str = "xy"):
        self._part = part
        self._entity = sketch_entity
        self._plane_name = plane_name
        self._editing = False
        self._drawing: Any = None
        self._geometry_added = False

    @property
    def entity(self) -> Any:
        return self._entity

    @property
    def plane_name(self) -> str:
        return self._plane_name

    def begin(self) -> "Sketch":
        if self._editing:
            return self
        fragment = self._entity.BeginEdit()
        view = fragment.ViewsAndLayersManager.Views.View(0)
        self._drawing = safe_cast(view, "IDrawingContainer")
        self._editing = True
        return self

    def end(self) -> "Sketch":
        if not self._editing:
            return self
        try:
            self._entity.EndEdit()
            self._entity.Update()
        finally:
            self._editing = False
            self._drawing = None
        return self

    def __enter__(self) -> "Sketch":
        return self.begin()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.end()

    def _drawing_container(self) -> Any:
        if not self._editing:
            self.begin()
        return self._drawing

    def _auto_end_if_needed(self, was_editing: bool) -> None:
        if not was_editing and self._editing:
            self.end()

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        was = self._editing
        drawing = self._drawing_container()
        try:
            circle = drawing.Circles.Add()
            circle = safe_cast(circle, "ICircle")
            circle.Xc = float(xc)
            circle.Yc = float(yc)
            circle.Radius = float(radius)
            circle.Style = int(style)
            circle.Update()
            self._geometry_added = True
        except Exception as e:
            self._auto_end_if_needed(was)
            raise KompasOperationError(f"Ошибка circle: {e}") from e
        self._auto_end_if_needed(was)
        return self

    def rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        style: int = 1,
    ) -> "Sketch":
        pts = [
            (x, y),
            (x + width, y),
            (x + width, y + height),
            (x, y + height),
        ]
        return self.polygon(pts, closed=True, style=style)

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        style: int = 1,
    ) -> "Sketch":
        was = self._editing
        drawing = self._drawing_container()
        try:
            line = drawing.Lines.Add()
            line = safe_cast(line, "ILineSegment")
            line.X1, line.Y1 = float(x1), float(y1)
            line.X2, line.Y2 = float(x2), float(y2)
            line.Style = int(style)
            line.Update()
            self._geometry_added = True
        except Exception as e:
            self._auto_end_if_needed(was)
            raise KompasOperationError(f"Ошибка line: {e}") from e
        self._auto_end_if_needed(was)
        return self

    def polygon(
        self,
        points: List[Tuple[float, float]],
        closed: bool = True,
        style: int = 1,
    ) -> "Sketch":
        if len(points) < 2:
            raise KompasOperationError("Нужно минимум 2 точки")

        was = self._editing
        drawing = self._drawing_container()
        try:
            n = len(points)
            count = n if closed else n - 1
            for i in range(count):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                line = drawing.Lines.Add()
                line = safe_cast(line, "ILineSegment")
                line.X1, line.Y1 = float(x1), float(y1)
                line.X2, line.Y2 = float(x2), float(y2)
                line.Style = int(style)
                line.Update()
            self._geometry_added = True
        except Exception as e:
            self._auto_end_if_needed(was)
            raise KompasOperationError(f"Ошибка polygon: {e}") from e
        self._auto_end_if_needed(was)
        return self
