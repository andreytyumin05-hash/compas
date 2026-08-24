"""
Высокоуровневый класс детали (Part).
"""

from __future__ import annotations

from typing import Any, Optional

from win32com.client import CastTo

from .connection import KompasApp, get_app
from .exceptions import KompasError, KompasOperationError
from .sketch import Sketch
from . import operations


# Имена плоскостей → константы o3d_plane*
_PLANE_MAP = {
    "xy": "o3d_planeXOY",
    "xoy": "o3d_planeXOY",
    "xz": "o3d_planeXOZ",
    "xoz": "o3d_planeXOZ",
    "yz": "o3d_planeYOZ",
    "yoz": "o3d_planeYOZ",
}


class Part:
    """
    Удобная обёртка над деталью КОМПАС-3D.

    Пример:
        from core import Part

        part = Part.create("Втулка")
        sk = part.sketch("xy")
        sk.circle(0, 0, 30)
        part.extrude(sk, depth=80)

        sk2 = part.sketch("xy")
        sk2.circle(0, 0, 15)
        part.cut(sk2, through_all=True)
    """

    def __init__(self, app: KompasApp, doc3d: Any):
        self.app = app
        self._doc3d = doc3d
        self._top_part = doc3d.TopPart
        self._container = CastTo(self._top_part, "IModelContainer")

    # ------------------------------------------------------------------
    # Создание
    # ------------------------------------------------------------------

    @classmethod
    def create(cls, name: str = "Деталь", app: Optional[KompasApp] = None) -> "Part":
        """Создать новую деталь."""
        if app is None:
            app = get_app(auto_launch=True)
        app.hide_messages(True)
        doc3d = app.new_part(name=name)
        return cls(app, doc3d)

    @classmethod
    def from_active(cls, app: Optional[KompasApp] = None) -> "Part":
        """Взять уже открытую активную деталь."""
        if app is None:
            app = get_app(auto_launch=False)
        doc = app.active_document
        if doc is None:
            raise KompasError("Нет активного документа")
        doc3d = CastTo(doc, "IKompasDocument3D")
        return cls(app, doc3d)

    # ------------------------------------------------------------------
    # Свойства
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        return str(self._top_part.Name)

    @name.setter
    def name(self, value: str) -> None:
        self._top_part.Name = str(value)
        self._top_part.Update()

    @property
    def top_part(self) -> Any:
        return self._top_part

    # ------------------------------------------------------------------
    # Эскизы
    # ------------------------------------------------------------------

    def sketch(self, plane: str = "xy") -> Sketch:
        """
        Создать новый эскиз на плоскости.

        plane: "xy" | "xz" | "yz" (или xoy/xoz/yoz)
        """
        plane_key = plane.lower().strip()
        const_name = _PLANE_MAP.get(plane_key)
        if not const_name:
            raise KompasOperationError(
                f"Неизвестная плоскость: {plane}. Используйте xy / xz / yz"
            )

        const = self.app.const3d
        plane_obj = self._top_part.DefaultObject(getattr(const, const_name))

        sketch_entity = CastTo(self._container.Sketchs.Add(), "ISketch")
        sketch_entity.Plane = plane_obj
        sketch_entity.Update()

        return Sketch(self, sketch_entity, plane_name=plane_key)

    # ------------------------------------------------------------------
    # Операции
    # ------------------------------------------------------------------

    def extrude(
        self,
        sketch: Sketch,
        depth: float,
        direction: str = "normal",
        both_directions: bool = False,
    ) -> Any:
        """Выдавить эскиз."""
        return operations.extrude(
            self, sketch, depth, direction=direction, both_directions=both_directions
        )

    def cut(
        self,
        sketch: Sketch,
        depth: float = 0.0,
        through_all: bool = False,
        direction: str = "normal",
    ) -> Any:
        """Вырезать по эскизу."""
        return operations.cut_extrude(
            self, sketch, depth=depth, through_all=through_all, direction=direction
        )

    def revolve(self, sketch: Sketch, angle: float = 360.0) -> Any:
        """Вращение эскиза."""
        return operations.revolve(self, sketch, angle=angle)

    def update(self) -> None:
        """Обновить модель."""
        self._top_part.Update()
