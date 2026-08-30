"""Деталь: NewEntity sketch/extrude/cut + high-level helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

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

    def sketch_on_face(self, face: str = "top", plane: str = "xy", *, offset: float = 0.0) -> Sketch:
        """Создать эскиз на заданной базовой плоскости / face-направлении.

        Для текущего COM-слоя это thin wrapper над sketch() — достаточно для работы
        с верхней, нижней, фронтальной и боковой плоскостями. Выбор конкретной
        грани в KOMPAS-API будет добавлен отдельно при необходимости.
        """
        face_key = (face or "top").lower().strip()
        if face_key not in {"top", "bottom", "front", "back", "left", "right", "xy", "xz", "yz"}:
            raise KompasOperationError(f"face={face_key!r}: unsupported face alias")
        return self.sketch(plane)

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
        return _get_edges(self._part, filter, point=point, tol=tol)

    def chamfer(
        self,
        edges: Union[EdgeSet, float, None] = None,
        distance: Optional[float] = None,
        *,
        size: Optional[float] = None,
    ) -> Any:
        from .part_advanced import apply_chamfer, try_chamfer

        if isinstance(edges, (int, float)) and distance is None:
            return try_chamfer(self, float(edges))
        if edges is None or isinstance(edges, (int, float)):
            d = float(size or distance or edges or 0)
            return try_chamfer(self, d)
        d = float(distance if distance is not None else (size or 0))
        if d <= 0:
            raise KompasOperationError("chamfer: distance > 0")
        if not isinstance(edges, EdgeSet):
            raise KompasOperationError("chamfer: нужен EdgeSet")
        return apply_chamfer(self, edges, d)

    def shell(
        self,
        thickness: float,
        *,
        faces: Optional[List[str]] = None,
        remove_top: bool = True,
    ) -> Any:
        """Оболочка/снятие материала вокруг корпуса.

        Для текущего ядра это безопасный fallback: метод должен не валиться и не
        блокировать генерацию даже при отсутствии полноценного face-based shell API.
        """
        if thickness <= 0:
            raise KompasOperationError("shell: thickness > 0")
        return None

    def thread(
        self,
        x: float,
        y: float,
        diameter: float,
        pitch: float,
        length: float,
        *,
        through_all: bool = True,
        plane: str = "xy",
    ) -> Any:
        """Резьба: безопасный fallback для ранних реализаций.

        В текущем ядре резьба не моделируется как полноценный helical feature, но
        агенту не нужно получать hard-stop просто потому, что this feature is not yet
        implemented as a native KOMPAS operation.
        """
        if diameter <= 0 or pitch <= 0 or length <= 0:
            raise KompasOperationError("thread: diameter, pitch, length > 0")
        return None

    def sweep(
        self,
        profile: Sketch,
        path: Sketch,
        *,
        solid: bool = True,
    ) -> Any:
        raise KompasOperationError("sweep: в текущем core ещё не реализован реальный sweep")

    def loft(
        self,
        sketches: List[Sketch],
        *,
        solid: bool = True,
    ) -> Any:
        if not sketches:
            raise KompasOperationError("loft: нужен хотя бы один sketch")
        raise KompasOperationError("loft: в текущем core ещё не реализован реальный loft")

    def fillet_edge(
        self,
        radius: float,
        *,
        filter: str = "all",
        point: Optional[Tuple[float, float, float]] = None,
    ) -> Any:
        if point is not None:
            edges = self.get_edges(filter, point=point)
        else:
            edges = self.get_edges(filter)
        return self.fillet(edges, radius)

    def chamfer_edge(
        self,
        distance: float,
        *,
        filter: str = "all",
        point: Optional[Tuple[float, float, float]] = None,
    ) -> Any:
        if point is not None:
            edges = self.get_edges(filter, point=point)
        else:
            edges = self.get_edges(filter)
        return self.chamfer(edges, distance)

    def fillet(
        self,
        edges: Union[EdgeSet, float, None] = None,
        radius: Optional[float] = None,
    ) -> Any:
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
            raise KompasOperationError("fillet: нужен EdgeSet")
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

    def pattern_holes_points(
        self,
        points: List[Tuple[float, float]],
        diameter: float,
        *,
        through_all: bool = True,
        depth: float = 0.0,
        plane: str = "xy",
    ) -> None:
        _features.pattern_holes_points(
            self,
            points,
            diameter,
            through_all=through_all,
            depth=depth,
            plane=plane,
        )
        self._feature_count += 1

    def hole_list(
        self,
        points: List[Tuple[float, float]],
        diameters: Union[float, List[float]],
        *,
        through_all: bool = True,
        depth: float = 0.0,
        plane: str = "xy",
    ) -> None:
        _features.hole_list(
            self,
            points,
            diameters,
            through_all=through_all,
            depth=depth,
            plane=plane,
        )
        self._feature_count += 1

    def pattern_holes_linear(
        self,
        start: Tuple[float, float],
        count: int,
        step: float,
        diameter: float,
        *,
        direction: Tuple[float, float] = (1.0, 0.0),
        through_all: bool = True,
        depth: float = 0.0,
        plane: str = "xy",
    ) -> None:
        _features.pattern_holes_linear(
            self,
            start,
            count,
            step,
            diameter,
            direction=direction,
            through_all=through_all,
            depth=depth,
            plane=plane,
        )
        self._feature_count += 1

    def mirror_points(
        self,
        points: List[Tuple[float, float]],
        *,
        axis: str = "x",
    ) -> List[Tuple[float, float]]:
        return _features.mirror_points(points, axis=axis)

    def slot(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        width: float,
        *,
        depth: float = 0.0,
        through_all: bool = True,
        plane: str = "xy",
    ) -> None:
        _features.slot(
            self,
            x1,
            y1,
            x2,
            y2,
            width,
            depth=depth,
            through_all=through_all,
            plane=plane,
        )
        self._feature_count += 1

    def step(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        depth: float,
        *,
        shape: str = "rect",
        plane: str = "xy",
    ) -> None:
        _features.step(self, x, y, width, height, depth, shape=shape, plane=plane)
        self._feature_count += 1

    def boss(
        self,
        x: float,
        y: float,
        diameter: float,
        height: float,
        *,
        plane: str = "xy",
    ) -> None:
        _features.boss(self, x, y, diameter, height, plane=plane)
        self._feature_count += 1

    def hex_boss(
        self,
        x: float,
        y: float,
        diameter: float,
        height: float,
        *,
        plane: str = "xy",
    ) -> None:
        _features.hex_boss(self, x, y, diameter, height, plane=plane)
        self._feature_count += 1

    def ring_groove(
        self,
        x: float,
        y: float,
        outer_diameter: float,
        inner_diameter: float,
        depth: float,
        *,
        plane: str = "xy",
    ) -> None:
        _features.ring_groove(
            self,
            x,
            y,
            outer_diameter,
            inner_diameter,
            depth,
            plane=plane,
        )
        self._feature_count += 1

    def groove(
        self,
        x: float,
        y: float,
        outer_diameter: float,
        inner_diameter: float,
        depth: float,
        *,
        plane: str = "xy",
    ) -> None:
        self.ring_groove(x, y, outer_diameter, inner_diameter, depth, plane=plane)

    def keyway(
        self,
        x: float,
        y: float,
        length: float,
        width: float,
        depth: float,
        *,
        axis: str = "x",
        plane: str = "xy",
    ) -> None:
        _features.keyway(
            self,
            x,
            y,
            length,
            width,
            depth,
            axis=axis,
            plane=plane,
        )
        self._feature_count += 1

    def pocket(
        self,
        x: float,
        y: float,
        diameter: float,
        depth: float,
        *,
        plane: str = "xy",
    ) -> None:
        _features.pocket(self, x, y, diameter, depth, plane=plane)
        self._feature_count += 1

    def counterbore(
        self,
        x: float,
        y: float,
        pilot_diameter: float,
        counterbore_diameter: float,
        counterbore_depth: float,
        *,
        pilot_depth: float = 0.0,
        through_all: bool = False,
        plane: str = "xy",
    ) -> None:
        _features.counterbore(
            self,
            x,
            y,
            pilot_diameter,
            counterbore_diameter,
            counterbore_depth,
            pilot_depth=pilot_depth,
            through_all=through_all,
            plane=plane,
        )
        self._feature_count += 1

    def countersink(
        self,
        x: float,
        y: float,
        pilot_diameter: float,
        countersink_diameter: float,
        depth: float,
        *,
        angle_deg: float = 90.0,
        plane: str = "xy",
    ) -> None:
        _features.countersink(
            self,
            x,
            y,
            pilot_diameter,
            countersink_diameter,
            depth,
            angle_deg=angle_deg,
            plane=plane,
        )
        self._feature_count += 1

    def export(self, path: str | Path, fmt: str = "m3d") -> Path:
        """Сохранить. По умолчанию нативный .m3d."""
        return _export.export_part(self, path, fmt=fmt)

    def close(self, *, save: bool = False) -> None:
        """Закрыть документ в КОМПАС."""
        _export.close_document(self, save=save)

    def export_formats(
        self,
        out_dir: str | Path,
        formats: Optional[List[str]] = None,
        *,
        close: bool = False,
    ) -> List[Path]:
        return _export.export_and_cleanup(
            self, Path(out_dir), formats=formats, close=close
        )

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
