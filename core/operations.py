"""
Выдавливание / вырезание — API5 NewEntity + SetSideParam + SetSketch + Create.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .connection import (
    O3D_BASE_EXTRUSION,
    O3D_BOSS_EXTRUSION,
    O3D_CUT_EXTRUSION,
    O3D_BOSS_ROTATED,
    DT_NORMAL,
    DT_REVERSE,
    DT_BOTH,
    ET_BLIND,
    ET_THROUGH_ALL,
)
from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part
    from .sketch import Sketch

DEBUG = os.environ.get("COMPAS_DEBUG_COM", "").lower() in ("1", "true", "yes")


def _log(msg: str) -> None:
    if DEBUG:
        print(f"[COM] {msg}")


def _set_side_param(definition: Any, through_all: bool, depth: float, direction: int) -> None:
    et = ET_THROUGH_ALL if through_all else ET_BLIND
    d = 0.0 if through_all else float(depth)
    last_err = None

    attempts = [
        ("SetSideParam(5args True)", lambda: definition.SetSideParam(True, et, d, 0, True)),
        ("SetSideParam(5args False)", lambda: definition.SetSideParam(True, et, d, 0.0, False)),
        ("SetSideParam(3args)", lambda: definition.SetSideParam(True, et, d)),
        (
            "SetSideParameters",
            lambda: definition.SetSideParameters(True, et, d, 0.0, False, None),
        ),
    ]

    for name, fn in attempts:
        try:
            fn()
            _log(f"side param via {name}")
            try:
                definition.directionType = direction
            except Exception:
                try:
                    definition.Direction = direction
                except Exception:
                    try:
                        ep = definition.ExtrusionParam()
                        ep.direction = direction
                        if not through_all:
                            ep.depthNormal = float(depth)
                    except Exception:
                        pass
            return
        except Exception as e:
            last_err = e
            _log(f"{name} failed: {e}")

    try:
        ep = definition.ExtrusionParam()
        ep.direction = direction
        if through_all:
            try:
                ep.typeNormal = ET_THROUGH_ALL
            except Exception:
                pass
        else:
            ep.depthNormal = float(depth)
            try:
                ep.typeNormal = ET_BLIND
            except Exception:
                pass
        _log("side param via ExtrusionParam only")
        return
    except Exception as e:
        raise KompasOperationError(
            f"Не задать параметры выдавливания. last={last_err}; ExtrusionParam={e}"
        ) from e


def extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float,
    direction: str = "normal",
    both_directions: bool = False,
) -> Any:
    type_id = O3D_BASE_EXTRUSION if part._feature_count == 0 else O3D_BOSS_EXTRUSION
    dir_id = DT_BOTH if both_directions else (DT_REVERSE if direction == "reverse" else DT_NORMAL)
    _log(f"extrude type_id={type_id} depth={depth}")

    try:
        entity = part._part.NewEntity(type_id)
        if entity is None:
            raise KompasOperationError(f"NewEntity({type_id}) вернул None")

        definition = entity.GetDefinition
        _set_side_param(definition, through_all=False, depth=depth, direction=dir_id)

        try:
            definition.SetThinParam(False, DT_NORMAL, 0, 0)
        except Exception as e:
            _log(f"SetThinParam skip: {e}")

        try:
            definition.SetSketch(sketch.entity)
        except Exception as e:
            raise KompasOperationError(f"SetSketch: {e}") from e

        ok = entity.Create
        if ok is False:
            raise KompasOperationError("entity.Create() вернул False (выдавливание)")
        _log("extrude Create OK")

        try:
            entity.Update
        except Exception as e:
            _log(f"entity.Update skip: {e}")

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
    type_id = O3D_CUT_EXTRUSION
    dir_id = DT_BOTH if through_all else (DT_REVERSE if direction == "reverse" else DT_NORMAL)
    _log(f"cut type_id={type_id} through_all={through_all}")

    try:
        entity = part._part.NewEntity(type_id)
        if entity is None:
            raise KompasOperationError("NewEntity(cutExtrusion) вернул None")

        definition = entity.GetDefinition
        _set_side_param(definition, through_all=through_all, depth=depth, direction=dir_id)

        try:
            definition.SetThinParam(False, DT_NORMAL, 0, 0)
        except Exception as e:
            _log(f"SetThinParam skip: {e}")

        try:
            definition.SetSketch(sketch.entity)
        except Exception as e:
            raise KompasOperationError(f"SetSketch (cut): {e}") from e

        ok = entity.Create
        if ok is False:
            raise KompasOperationError("entity.Create() вернул False (вырезание)")

        try:
            entity.Update
        except Exception as e:
            _log(f"entity.Update skip: {e}")

        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Вырезание: {e}") from e


def revolve(part: "Part", sketch: "Sketch", angle: float = 360.0) -> Any:
    try:
        entity = part._part.NewEntity(O3D_BOSS_ROTATED)
        definition = entity.GetDefinition
        try:
            definition.SetSketch(sketch.entity)
        except Exception as e:
            raise KompasOperationError(f"SetSketch (revolve): {e}") from e
        try:
            definition.angle = float(angle)
        except Exception as e:
            _log(f"angle skip: {e}")
        entity.Create
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Вращение: {e}") from e
