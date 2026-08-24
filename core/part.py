"""
Деталь через API5: GetPart + NewEntity.
"""

from __future__ import annotations

from typing import Any, Optional

from .connection import (
    KompasApp,
    get_app,
    O3D_PLANE_XOY,
    O3D_PLANE_XOZ,
    O3D_PLANE_YOZ,
    O3D_SKETCH,
)
from .exceptions import KompasError, KompasOperationError
from .sketch import Sketch
from . import operations

_PLANES = {
    "xy": O3D_PLANE_XOY,
    "xoy": O3D_PLANE_XOY,
    "xz": O3D_PLANE_XOZ,
    "xoz": O3D_PLANE_XOZ,
    "yz": O3D_PLANE_YOZ,
    "yoz": O3D_PLANE_YOZ,
}


class Part:
    def __init__(self, app: KompasApp, doc3d: Any, part_com: Any, name: str = ""):
        self.app = app
        self._doc3d = doc3d
        self._part = part_com  # ksPart
        self._name = name
        self._feature_count = 0  # сколько формообразующих уже создано

    @classmethod
    def create(cls, name: str = "Деталь", app: Optional[KompasApp] = None) -> "Part":
        if app is None:
            app = get_app(auto_launch=True)
        app.hide_messages(True)
        doc3d, part_com = app.new_part_document()

        # Имя — best effort (на API5 иногда через part.name)
        if name:
            for attr in ("name", "Name"):
                try:
                    setattr(part_com, attr, str(name))
                    break
                except Exception:
                    continue

        return cls(app, doc3d, part_com, name=name)

    @classmethod
    def from_active(cls, app: Optional[KompasApp] = None) -> "Part":
        if app is None:
            app = get_app(auto_launch=False)
        try:
            doc3d = app.k5.ActiveDocument3D()
            part_com = doc3d.GetPart(-1)
        except Exception as e:
            raise KompasError(f"Нет активной 3D-детали: {e}") from e
        return cls(app, doc3d, part_com)

    @property
    def top_part(self) -> Any:
        return self._part

    @property
    def name(self) -> str:
        for attr in ("name", "Name"):
            try:
                return str(getattr(self._part, attr))
            except Exception:
                continue
        return self._name or ""

    @name.setter
    def name(self, value: str) -> None:
        self._name = str(value)
        for attr in ("name", "Name"):
            try:
                setattr(self._part, attr, str(value))
                return
            except Exception:
                continue

    def sketch(self, plane: str = "xy") -> Sketch:
        plane_key = plane.lower().strip()
        plane_id = _PLANES.get(plane_key)
        if plane_id is None:
            raise KompasOperationError(f"Плоскость {plane!r}: используйте xy/xz/yz")

        try:
            entity = self._part.NewEntity(O3D_SKETCH)
        except Exception as e:
            raise KompasOperationError(f"NewEntity(sketch) не удался: {e}") from e

        if entity is None:
            raise KompasOperationError("NewEntity(sketch) вернул None")

        try:
            definition = entity.GetDefinition()
        except Exception as e:
            raise KompasOperationError(f"GetDefinition эскиза: {e}") from e

        try:
            plane_entity = self._part.GetDefaultEntity(plane_id)
        except Exception as e:
            raise KompasOperationError(
                f"GetDefaultEntity({plane_id}) не удался: {e}"
            ) from e

        try:
            definition.SetPlane(plane_entity)
        except Exception as e:
            raise KompasOperationError(f"SetPlane: {e}") from e

        # Create эскиза до рисования — как в примерах SDK
        try:
            entity.Create()
        except Exception:
            pass

        return Sketch(self, entity, definition, plane_name=plane_key)

    def extrude(
        self,
        sketch: Sketch,
        depth: float,
        direction: str = "normal",
        both_directions: bool = False,
    ) -> Any:
        result = operations.extrude(
            self, sketch, depth, direction=direction, both_directions=both_directions
        )
        self._feature_count += 1
        return result

    def cut(
        self,
        sketch: Sketch,
        depth: float = 0.0,
        through_all: bool = False,
        direction: str = "normal",
    ) -> Any:
        result = operations.cut_extrude(
            self, sketch, depth=depth, through_all=through_all, direction=direction
        )
        self._feature_count += 1
        return result

    def revolve(self, sketch: Sketch, angle: float = 360.0) -> Any:
        result = operations.revolve(self, sketch, angle=angle)
        self._feature_count += 1
        return result

    def update(self) -> None:
        try:
            self._doc3d.UpdateDocumentParam()
        except Exception:
            pass
        try:
            self._part.Update()
        except Exception:
            pass
