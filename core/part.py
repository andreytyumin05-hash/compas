"""Деталь: NewEntity sketch/extrude/cut + high-level helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

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
from .edges import EdgeSet, get_edges as _get_edges
from . import operations
from . import features as _features
from . import export as _export
from . import mass as _mass

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
        if depth == 0 and not both_directions:
            raise KompasOperationError("extrude: depth не должен быть 0")
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
        if not through_all and depth <= 0:
            raise KompasOperationError("cut: нужен depth > 0 или through_all=True")
        result = operations.cut_extrude(
            self, sketch, depth=depth, through_all=through_all, direction=direction
        )
        self._feature_count += 1
        return result

    def revolve(self, sketch: Sketch, angle: float = 360.0) -> Any:
        result = operations.revolve(self, sketch, angle=angle)
        self._feature_count += 1
        return result

    def get_edges(
        self,
        filter: str = "all",
        *,
        point: Optional[Tuple[float, float, float]] = None,
        tol: float = 1.0,
    ) -> EdgeSet:
        """
        Рёбра тела по предикату (не сырые COM-ID).

        filter: all | parallel_x/y/z | near_point | top_z | bottom_z

        Example:
            edges = part.get_edges("all")
            edges = part.get_edges("parallel_z")
            edges = part.get_edges("near_point", point=(0, 0, 25), tol=2)
        """
        return _get_edges(self._part, filter, point=point, tol=tol)

    def chamfer(
        self,
        edges: Union[EdgeSet, float, None] = None,
        distance: Optional[float] = None,
        *,
        size: Optional[float] = None,
    ) -> Any:
        """
        Фаска по EdgeSet.

        Example:
            part.chamfer(part.get_edges("all"), distance=1.0)
            part.chamfer(size=1.0)  # все рёбра (совместимость)
        """
        from .part_advanced import apply_chamfer, try_chamfer

        # legacy: chamfer(size=1.0) or chamfer(1.0)
        if isinstance(edges, (int, float)) and distance is None:
            return try_chamfer(self, float(edges))
        if edges is None or isinstance(edges, (int, float)):
            d = float(size or distance or edges or 0)
            return try_chamfer(self, d)
        d = float(distance if distance is not None else (size or 0))
        if d <= 0:
            raise KompasOperationError("chamfer: distance > 0")
        if not isinstance(edges, EdgeSet):
            raise KompasOperationError("chamfer: нужен EdgeSet из part.get_edges(...)")
        return apply_chamfer(self, edges, d)

    def fillet(
        self,
        edges: Union[EdgeSet, float, None] = None,
        radius: Optional[float] = None,
    ) -> Any:
        """
        Скругление по EdgeSet.

        Example:
            part.fillet(part.get_edges("all"), radius=1.0)
            part.fillet(radius=1.0)  # все рёбра
        """
        from .part_advanced import apply_fillet, try_fillet

        if isinstance(edges, (int, float)) and radius is None:
            return try_fillet(self, float(edges))
        if edges is None or isinstance(edges, (int, float)):
            r = float(radius if radius is not None else edges or 0)
            return try_fillet(self, r)
        r = float(radius or 0)
        if r <= 0:
            raise KompasOperationError("fillet: radius > 0")
        if not isinstance(edges, EdgeSet):
            raise KompasOperationError("fillet: нужен EdgeSet из part.get_edges(...)")
        return apply_fillet(self, edges, r)

    def hole(
        self,
        x: float,
        y: float,
        diameter: float,
        *,
        depth: float = 0.0,
        through_all: bool = True,
        plane: str = "xy",
    ) -> None:
        _features.hole(
            self, x, y, diameter, depth=depth, through_all=through_all, plane=plane
        )

    def pattern_holes_circular(
        self,
        center: Tuple[float, float],
        pcd: float,
        count: int,
        diameter: float,
        *,
        start_angle_deg: float = 0.0,
        through_all: bool = True,
        depth: float = 0.0,
        plane: str = "xy",
    ) -> None:
        _features.pattern_holes_circular(
            self,
            center,
            pcd,
            count,
            diameter,
            start_angle_deg=start_angle_deg,
            through_all=through_all,
            depth=depth,
            plane=plane,
        )

    def pattern_holes_rect(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        diameter: float,
        *,
        through_all: bool = True,
        depth: float = 0.0,
        plane: str = "xy",
    ) -> None:
        _features.pattern_holes_rect(
            self,
            x1,
            y1,
            x2,
            y2,
            diameter,
            through_all=through_all,
            depth=depth,
            plane=plane,
        )

    def export(self, path: str | Path, fmt: str = "step") -> Path:
        return _export.export_part(self, path, fmt=fmt)

    def mass_properties(self) -> Dict[str, Any]:
        return _mass.get_mass_properties(self)

    def update(self) -> None:
        try:
            self._doc3d.UpdateDocumentParam
        except Exception:
            pass
        try:
            self._part.Update
        except Exception:
            pass
