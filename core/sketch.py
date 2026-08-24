"""
Эскиз API5: BeginEdit → ksCircle / ksLineSeg → EndEdit.
"""

from __future__ import annotations

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
            self._doc2d = self._definition.BeginEdit()
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
            self._definition.EndEdit()
        except Exception as e:
            raise KompasOperationError(f"EndEdit эскиза: {e}") from e
        finally:
            self._editing = False
            self._doc2d = None
        try:
            self._entity.Update()
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
        """
        Окружность. style=1 — основная линия (обязательно для контура).
        API5: doc2d.ksCircle(x, y, r, style)
        """
        was = self._editing
        doc2d = self._ensure()
        try:
            # Основной путь SDK
            result = doc2d.ksCircle(float(xc), float(yc), float(radius), int(style))
            if result == 0:
                # 0 часто значит ошибка в ks*
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
                # line сам управляет сессией — держим открытой
                doc2d = self._doc2d
                r = doc2d.ksLineSeg(float(x1), float(y1), float(x2), float(y2), int(style))
                if r == 0:
                    raise KompasOperationError("ksLineSeg вернул 0 в polygon")
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"polygon: {e}") from e
        self._auto_end(was)
        return self
