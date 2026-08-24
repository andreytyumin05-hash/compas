"""
Высокоуровневый класс детали (Part).
"""

from __future__ import annotations

from typing import Any, Optional

from .comutil import safe_cast
from .connection import KompasApp, get_app
from .exceptions import KompasError, KompasOperationError
from .sketch import Sketch
from . import operations

_PLANE_MAP = {
    "xy": "o3d_planeXOY",
    "xoy": "o3d_planeXOY",
    "xz": "o3d_planeXOZ",
    "xoz": "o3d_planeXOZ",
    "yz": "o3d_planeYOZ",
    "yoz": "o3d_planeYOZ",
}


class Part:
    def __init__(self, app: KompasApp, doc3d: Any):
        self.app = app
        self._doc3d = doc3d
        self._top_part = doc3d.TopPart
        # IModelContainer = тот же TopPart в late binding
        self._container = safe_cast(self._top_part, "IModelContainer")

    @classmethod
    def create(cls, name: str = "Деталь", app: Optional[KompasApp] = None) -> "Part":
        if app is None:
            app = get_app(auto_launch=True)
        app.hide_messages(True)
        doc3d = app.new_part(name=name)
        return cls(app, doc3d)

    @classmethod
    def from_active(cls, app: Optional[KompasApp] = None) -> "Part":
        if app is None:
            app = get_app(auto_launch=False)
        doc = app.active_document
        if doc is None:
            raise KompasError("Нет активного документа")
        return cls(app, safe_cast(doc, "IKompasDocument3D"))

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

    def sketch(self, plane: str = "xy") -> Sketch:
        plane_key = plane.lower().strip()
        const_name = _PLANE_MAP.get(plane_key)
        if not const_name:
            raise KompasOperationError(
                f"Неизвестная плоскость: {plane}. Используйте xy / xz / yz"
            )

        const = self.app.const3d
        plane_id = getattr(const, const_name)
        plane_obj = self._top_part.DefaultObject(plane_id)

        # Sketchs (с опечаткой API) или Sketches — пробуем оба
        sketches = None
        for attr in ("Sketchs", "Sketches"):
            sketches = getattr(self._container, attr, None)
            if sketches is not None:
                break
        if sketches is None:
            raise KompasOperationError(
                "Не найдены Sketchs/Sketches у TopPart — проверьте версию API"
            )

        sketch_entity = sketches.Add()
        sketch_entity = safe_cast(sketch_entity, "ISketch")
        sketch_entity.Plane = plane_obj
        sketch_entity.Update()

        return Sketch(self, sketch_entity, plane_name=plane_key)

    def extrude(
        self,
        sketch: Sketch,
        depth: float,
        direction: str = "normal",
        both_directions: bool = False,
    ) -> Any:
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
        return operations.cut_extrude(
            self, sketch, depth=depth, through_all=through_all, direction=direction
        )

    def revolve(self, sketch: Sketch, angle: float = 360.0) -> Any:
        return operations.revolve(self, sketch, angle=angle)

    def update(self) -> None:
        self._top_part.Update()
