"""
Рисование в эскизе через 2D API фрагмента эскиза.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Tuple

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part


class Sketch:
    def __init__(self, part: "Part", sketch_entity: Any, plane_name: str = "xy"):
        self._part = part
        self._entity = sketch_entity
        self._plane_name = plane_name
        self._editing = False
        self._editor: Any = None  # 2D document / drawing container

    @property
    def entity(self) -> Any:
        return self._entity

    @property
    def plane_name(self) -> str:
        return self._plane_name

    def begin(self) -> "Sketch":
        if self._editing:
            return self

        editor = None
        errors = []

        # Вариант A: BeginEdit на entity (API7)
        try:
            editor = self._entity.BeginEdit()
        except Exception as e:
            errors.append(f"BeginEdit: {e}")

        # Вариант B: GetDefinition().BeginEdit()
        if editor is None:
            try:
                definition = self._entity.GetDefinition()
                editor = definition.BeginEdit()
            except Exception as e:
                errors.append(f"GetDefinition.BeginEdit: {e}")

        if editor is None:
            raise KompasOperationError(
                "Не открыть эскиз на редактирование: " + "; ".join(errors)
            )

        self._editor = editor
        self._editing = True
        return self

    def end(self) -> "Sketch":
        if not self._editing:
            return self
        try:
            try:
                self._entity.EndEdit()
            except Exception:
                try:
                    self._entity.GetDefinition().EndEdit()
                except Exception:
                    pass
            try:
                self._entity.Update()
            except Exception:
                pass
            try:
                self._entity.Create()
            except Exception:
                pass
        finally:
            self._editing = False
            self._editor = None
        return self

    def __enter__(self) -> "Sketch":
        return self.begin()

    def __exit__(self, exc_type, exc, tb) -> None:
        self.end()

    def _ensure_edit(self) -> Any:
        if not self._editing:
            self.begin()
        return self._editor

    def _auto_end(self, was: bool) -> None:
        if not was and self._editing:
            self.end()

    def _draw_circle_api5(self, editor: Any, xc: float, yc: float, radius: float) -> None:
        """
        Пробуем несколько способов нарисовать окружность
        (разные версии отдают разный editor).
        """
        # 1) IDrawingContainer.Circles
        try:
            circles = editor.Circles
            c = circles.Add()
            c.Xc, c.Yc, c.Radius = float(xc), float(yc), float(radius)
            try:
                c.Style = 1
            except Exception:
                pass
            c.Update()
            return
        except Exception:
            pass

        # 2) Views → View(0) → Circles
        try:
            view = editor.ViewsAndLayersManager.Views.View(0)
            circles = view.Circles
            c = circles.Add()
            c.Xc, c.Yc, c.Radius = float(xc), float(yc), float(radius)
            try:
                c.Style = 1
            except Exception:
                pass
            c.Update()
            return
        except Exception:
            pass

        # 3) ksDocument2D style: kompas.Document2D + ksCircle
        # editor иногда сам является 2D doc с методами Circle
        for method in ("ksCircle", "Circle"):
            fn = getattr(editor, method, None)
            if callable(fn):
                try:
                    fn(float(xc), float(yc), float(radius), 1)
                    return
                except Exception:
                    pass

        raise KompasOperationError(
            "Не удалось нарисовать окружность: неизвестный интерфейс редактора эскиза"
        )

    def circle(self, xc: float, yc: float, radius: float, style: int = 1) -> "Sketch":
        was = self._editing
        editor = self._ensure_edit()
        try:
            self._draw_circle_api5(editor, xc, yc, radius)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"circle: {e}") from e
        self._auto_end(was)
        return self

    def line(self, x1: float, y1: float, x2: float, y2: float, style: int = 1) -> "Sketch":
        was = self._editing
        editor = self._ensure_edit()
        try:
            try:
                lines = editor.Lines
                ln = lines.Add()
                ln.X1, ln.Y1 = float(x1), float(y1)
                ln.X2, ln.Y2 = float(x2), float(y2)
                try:
                    ln.Style = int(style)
                except Exception:
                    pass
                ln.Update()
            except Exception:
                view = editor.ViewsAndLayersManager.Views.View(0)
                ln = view.Lines.Add()
                ln.X1, ln.Y1 = float(x1), float(y1)
                ln.X2, ln.Y2 = float(x2), float(y2)
                ln.Update()
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"line: {e}") from e
        self._auto_end(was)
        return self

    def rectangle(self, x: float, y: float, width: float, height: float, style: int = 1) -> "Sketch":
        pts = [(x, y), (x + width, y), (x + width, y + height), (x, y + height)]
        return self.polygon(pts, closed=True, style=style)

    def polygon(self, points: List[Tuple[float, float]], closed: bool = True, style: int = 1) -> "Sketch":
        if len(points) < 2:
            raise KompasOperationError("Нужно >= 2 точек")
        was = self._editing
        self._ensure_edit()
        try:
            n = len(points)
            count = n if closed else n - 1
            for i in range(count):
                x1, y1 = points[i]
                x2, y2 = points[(i + 1) % n]
                self.line(x1, y1, x2, y2, style=style)
        except Exception as e:
            self._auto_end(was)
            raise KompasOperationError(f"polygon: {e}") from e
        # line() мог закрыть сессию — если была открыта снаружи, начнём снова не нужно
        if was and not self._editing:
            self.begin()
        elif not was and self._editing:
            self.end()
        return self
