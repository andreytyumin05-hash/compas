"""Деталь: NewEntity sketch/extrude/cut."""

from __future__ import annotations

from typing import Any, Optional

from .connection import (
    KompasApp,
    get_app,
    O3D_PLANE_XOY,
    O3D_PLANE_XOZ,
    O3D_PLANE_YOZ,
    O3D_SKETCH,
    _as_prop_or_call,
    _extract_part,
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
        self._part = part_com
        self._name = name
        self._feature_count = 0

    @classmethod
    def create(cls, name: str = "Деталь", app: Optional[KompasApp] = None) -> "Part":
        if app is None:
            app = get_app(auto_launch=True)
        app.hide_messages(True)
        doc3d, part_com = app.new_part_document()

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

        errors: list[str] = []

        if app.app7 is not None:
            try:
                ad = app.app7.ActiveDocument
                part_com, how = _extract_part(ad, require_legacy_part=True)
                if part_com is not None:
                    return cls(app, ad, part_com)
                errors.append(f"app7.ActiveDocument: {how}")
            except Exception as e:
                errors.append(f"app7: {e}")

        if app.k5 is not None:
            try:
                d3 = _as_prop_or_call(app.k5, "ActiveDocument3D")
                part_com, how = _extract_part(d3, require_legacy_part=True)
                if part_com is not None:
                    return cls(app, d3, part_com)
                errors.append(f"ActiveDocument3D: {how}")
            except Exception as e:
                errors.append(f"k5: {e}")

        raise KompasError(
            "Нет активной 3D-детали. Откройте Деталь в КОМПАСе.\n"
            + "\n".join(f"  • {e}" for e in errors)
        )

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
            raise KompasOperationError(f"Плоскость {plane!r}: xy/xz/yz")

        try:
            entity = self._part.NewEntity(O3D_SKETCH)
        except Exception as e:
            raise KompasOperationError(f"NewEntity(sketch): {e}") from e
        if entity is None:
            raise KompasOperationError("NewEntity(sketch) None")

        try:
            definition = entity.GetDefinition
        except Exception as e:
            raise KompasOperationError(f"GetDefinition: {e}") from e

        try:
            plane_entity = self._part.GetDefaultEntity(plane_id)
            definition.SetPlane(plane_entity)
        except Exception as e:
            raise KompasOperationError(f"SetPlane: {e}") from e

        try:
            entity.Create
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

    def chamfer(self, size: float = 1.0) -> Any:
        from .part_advanced import try_chamfer

        return try_chamfer(self, size)

    def fillet(self, radius: float = 1.0) -> Any:
        from .part_advanced import try_fillet

        return try_fillet(self, radius)

    def update(self) -> None:
        try:
            self._doc3d.UpdateDocumentParam
        except Exception:
            pass
        try:
            self._part.Update
        except Exception:
            pass
