"""
Класс детали. Эскизы через NewEntity (API5-стиль) — надёжнее на v23.
"""

from __future__ import annotations

from typing import Any, Optional

from .connection import KompasApp, get_app
from .exceptions import KompasError, KompasOperationError
from .sketch import Sketch
from . import operations
from .constants_resolve import CONST3D

_PLANE_ATTR = {
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
        return cls(app, doc)

    @property
    def name(self) -> str:
        return str(self._top_part.Name)

    @name.setter
    def name(self, value: str) -> None:
        self._top_part.Name = str(value)
        try:
            self._top_part.Update()
        except Exception:
            pass

    @property
    def top_part(self) -> Any:
        return self._top_part

    def sketch(self, plane: str = "xy") -> Sketch:
        plane_key = plane.lower().strip()
        attr = _PLANE_ATTR.get(plane_key)
        if not attr:
            raise KompasOperationError(f"Плоскость {plane!r} неизвестна (xy/xz/yz)")

        plane_id = CONST3D.get(attr)
        try:
            plane_obj = self._top_part.DefaultObject(plane_id)
        except Exception as e:
            raise KompasOperationError(
                f"DefaultObject({attr}={plane_id}) не удался: {e}. "
                f"Источник констант: {CONST3D.source}"
            ) from e

        # --- путь 1: NewEntity(o3d_sketch) — классика API
        sketch_entity = None
        err1 = None
        try:
            sketch_id = CONST3D.get("o3d_sketch")
            sketch_entity = self._top_part.NewEntity(sketch_id)
        except Exception as e:
            err1 = e

        # --- путь 2: коллекция Sketchs/Sketches
        if sketch_entity is None:
            for coll_name in ("Sketchs", "Sketches"):
                coll = getattr(self._top_part, coll_name, None)
                if coll is None:
                    continue
                try:
                    sketch_entity = coll.Add()
                    break
                except Exception as e:
                    err1 = e

        if sketch_entity is None:
            raise KompasOperationError(
                f"Не удалось создать эскиз. NewEntity/Sketchs ошибка: {err1}"
            )

        # Параметры эскиза
        try:
            # API5: GetDefinition → ksSketchDefinition
            definition = sketch_entity.GetDefinition()
            definition.SetPlane(plane_obj)
            try:
                definition.BeginEdit()
            except Exception:
                pass
            # некоторые версии: Plane на entity
        except Exception:
            try:
                sketch_entity.Plane = plane_obj
            except Exception as e:
                raise KompasOperationError(f"Не задать плоскость эскиза: {e}") from e

        try:
            sketch_entity.Create()
        except Exception:
            pass
        try:
            sketch_entity.Update()
        except Exception:
            pass

        return Sketch(self, sketch_entity, plane_name=plane_key)

    def extrude(self, sketch: Sketch, depth: float, direction: str = "normal", both_directions: bool = False) -> Any:
        return operations.extrude(self, sketch, depth, direction=direction, both_directions=both_directions)

    def cut(self, sketch: Sketch, depth: float = 0.0, through_all: bool = False, direction: str = "normal") -> Any:
        return operations.cut_extrude(self, sketch, depth=depth, through_all=through_all, direction=direction)

    def revolve(self, sketch: Sketch, angle: float = 360.0) -> Any:
        return operations.revolve(self, sketch, angle=angle)

    def update(self) -> None:
        try:
            self._top_part.Update()
        except Exception:
            pass
