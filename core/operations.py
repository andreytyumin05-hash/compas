"""
Выдавливание / вырезание через NewEntity (предпочтительно) или Extrusions.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .constants_resolve import CONST3D
from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part
    from .sketch import Sketch


def _new_entity(part: "Part", type_id: int) -> Any:
    try:
        return part._top_part.NewEntity(type_id)
    except Exception as e:
        raise KompasOperationError(f"NewEntity({type_id}) не удался: {e}") from e


def _finish_entity(entity: Any, part: "Part") -> None:
    try:
        entity.Create()
    except Exception:
        pass
    try:
        entity.Update()
    except Exception:
        pass
    try:
        part._top_part.Update()
    except Exception:
        pass


def extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float,
    direction: str = "normal",
    both_directions: bool = False,
) -> Any:
    type_id = CONST3D.get("o3d_bossExtrusion")
    dt = CONST3D.get("dtBoth" if both_directions else ("dtReverse" if direction == "reverse" else "dtNormal"))
    et = CONST3D.get("etBlind")

    try:
        entity = _new_entity(part, type_id)
        definition = entity.GetDefinition()

        # привязка эскиза
        try:
            definition.SetSketch(sketch.entity)
        except Exception:
            try:
                definition.Sketch = sketch.entity
            except Exception as e:
                raise KompasOperationError(f"SetSketch: {e}") from e

        # направление и глубина — разные сигнатуры API
        applied = False
        try:
            definition.directionType = dt
        except Exception:
            try:
                definition.Direction = dt
            except Exception:
                pass

        # SetSideParam / SetSideParameters
        for method_name in ("SetSideParameters", "SetSideParam"):
            method = getattr(definition, method_name, None)
            if not callable(method):
                continue
            try:
                # частый вариант API7
                method(True, et, float(depth), 0.0, False, None)
                applied = True
                break
            except Exception:
                try:
                    method(True, et, float(depth))
                    applied = True
                    break
                except Exception:
                    continue

        if not applied:
            # ksExtrusionParam
            try:
                prop = definition.ExtrusionParam()
                prop.depthNormal = float(depth)
                try:
                    prop.direction = dt
                except Exception:
                    pass
            except Exception as e:
                raise KompasOperationError(
                    f"Не задать глубину выдавливания: {e}"
                ) from e

        _finish_entity(entity, part)
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Выдавливание: {e}") from e


def cut_extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float = 0.0,
    through_all: bool = False,
    direction: str = "normal",
) -> Any:
    type_id = CONST3D.get("o3d_cutExtrusion")
    dt = CONST3D.get("dtBoth" if through_all else ("dtReverse" if direction == "reverse" else "dtNormal"))
    et = CONST3D.get("etThroughAll" if through_all else "etBlind")

    try:
        entity = _new_entity(part, type_id)
        definition = entity.GetDefinition()

        try:
            definition.SetSketch(sketch.entity)
        except Exception:
            definition.Sketch = sketch.entity

        try:
            definition.directionType = dt
        except Exception:
            try:
                definition.Direction = dt
            except Exception:
                pass

        applied = False
        depth_val = 0.0 if through_all else float(depth)
        for method_name in ("SetSideParameters", "SetSideParam"):
            method = getattr(definition, method_name, None)
            if not callable(method):
                continue
            try:
                method(True, et, depth_val, 0.0, False, None)
                applied = True
                break
            except Exception:
                try:
                    method(True, et, depth_val)
                    applied = True
                    break
                except Exception:
                    continue

        if not applied and not through_all:
            try:
                prop = definition.ExtrusionParam()
                prop.depthNormal = float(depth)
            except Exception as e:
                raise KompasOperationError(f"Не задать параметры выреза: {e}") from e

        _finish_entity(entity, part)
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Вырезание: {e}") from e


def revolve(part: "Part", sketch: "Sketch", angle: float = 360.0) -> Any:
    type_id = CONST3D.get("o3d_bossRotated")
    try:
        entity = _new_entity(part, type_id)
        definition = entity.GetDefinition()
        try:
            definition.SetSketch(sketch.entity)
        except Exception:
            definition.Sketch = sketch.entity
        try:
            definition.Angle = float(angle)
        except Exception:
            pass
        _finish_entity(entity, part)
        return entity
    except Exception as e:
        raise KompasOperationError(f"Вращение: {e}") from e
