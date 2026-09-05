"""
Выдавливание / вырезание — API5 NewEntity + SetSideParam + SetSketch + Create.

Критические правила:
- through_all для выреза — это тип окончания, а не DT_BOTH;
- базовая деталь вращения создаётся через o3d_baseRotated, последующие тела —
  через o3d_bossRotated;
- успех операции проверяется по Create, а не только по отсутствию исключения.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .connection import (
    O3D_BASE_EXTRUSION,
    O3D_BOSS_EXTRUSION,
    O3D_CUT_EXTRUSION,
    O3D_BASE_ROTATED,
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


def _created_ok(result: Any) -> bool:
    if result is False or result is None:
        return False
    try:
        return bool(int(result))
    except Exception:
        return True


def _set_side_param(definition: Any, through_all: bool, depth: float, direction: int) -> None:
    et = ET_THROUGH_ALL if through_all else ET_BLIND
    d = 0.0 if through_all else float(depth)
    last_err = None

    attempts = [
        ("SetSideParam(5args)", lambda: definition.SetSideParam(True, et, d, 0, False)),
        ("SetSideParam(3args)", lambda: definition.SetSideParam(True, et, d)),
        ("SetSideParameters", lambda: definition.SetSideParameters(True, et, d, 0.0, False, None)),
    ]

    for name, fn in attempts:
        try:
            if fn() is False:
                raise RuntimeError("returned FALSE")
            _log(f"side param via {name}")
            # For cut extrusion, direction is controlled separately.  For a
            # through-all cut, keep a single normal direction; DT_BOTH is not
            # equivalent to ET_THROUGH_ALL and can leave material behind.
            for member, value in (("directionType", direction), ("Direction", direction)):
                try:
                    setattr(definition, member, direction)
                    break
                except Exception:
                    pass
            return
        except Exception as exc:
            last_err = exc
            _log(f"{name} failed: {exc}")

    try:
        ep = definition.ExtrusionParam()
        try:
            ep.direction = direction
        except Exception:
            pass
        if through_all:
            try:
                ep.typeNormal = ET_THROUGH_ALL
            except Exception:
                pass
        else:
            try:
                ep.typeNormal = ET_BLIND
            except Exception:
                pass
            try:
                ep.depthNormal = float(depth)
            except Exception:
                pass
        _log("side param via ExtrusionParam")
        return
    except Exception as exc:
        raise KompasOperationError(
            f"Не задать параметры выдавливания. last={last_err}; ExtrusionParam={exc}"
        ) from exc


def _set_rotated_side_param(definition: Any, angle: float, direction: int = DT_NORMAL) -> None:
    last_err = None
    for fn in (
        lambda: definition.SetSideParam(True, float(angle)),
        lambda: definition.SetSideParam(True, float(angle), 0),
    ):
        try:
            result = fn()
            if result is False:
                raise RuntimeError("returned FALSE")
            return
        except Exception as exc:
            last_err = exc
    for member, value in (("directionType", direction), ("Direction", direction), ("angle", float(angle))):
        try:
            setattr(definition, member, value)
        except Exception:
            pass
    if last_err:
        _log(f"rotated SetSideParam fallback: {last_err}")


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
        except Exception as exc:
            _log(f"SetThinParam skip: {exc}")
        try:
            definition.SetSketch(sketch.entity)
        except Exception as exc:
            raise KompasOperationError(f"SetSketch: {exc}") from exc
        result = entity.Create
        if not _created_ok(result):
            raise KompasOperationError(f"entity.Create failed for extrusion: {result!r}")
        try:
            entity.Update
        except Exception as exc:
            _log(f"entity.Update skip: {exc}")
        return entity
    except KompasOperationError:
        raise
    except Exception as exc:
        raise KompasOperationError(f"Выдавливание: {exc}") from exc


def cut_extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float = 0.0,
    through_all: bool = False,
    direction: str = "normal",
) -> Any:
    type_id = O3D_CUT_EXTRUSION
    # through_all is an End_Type. Direction remains normal/reverse; do not
    # replace it by DT_BOTH because KOMPAS interprets those as different axes.
    dir_id = DT_REVERSE if direction == "reverse" else DT_NORMAL
    _log(f"cut type_id={type_id} through_all={through_all} direction={dir_id}")

    try:
        entity = part._part.NewEntity(type_id)
        if entity is None:
            raise KompasOperationError("NewEntity(cutExtrusion) вернул None")
        definition = entity.GetDefinition
        _set_side_param(definition, through_all=through_all, depth=depth, direction=dir_id)
        try:
            definition.SetThinParam(False, DT_NORMAL, 0, 0)
        except Exception as exc:
            _log(f"SetThinParam skip: {exc}")
        try:
            definition.SetSketch(sketch.entity)
        except Exception as exc:
            raise KompasOperationError(f"SetSketch (cut): {exc}") from exc
        result = entity.Create
        if not _created_ok(result):
            raise KompasOperationError(f"entity.Create failed for cut: {result!r}")
        try:
            entity.Update
        except Exception as exc:
            _log(f"entity.Update skip: {exc}")
        return entity
    except KompasOperationError:
        raise
    except Exception as exc:
        raise KompasOperationError(f"Вырезание: {exc}") from exc


def revolve(part: "Part", sketch: "Sketch", angle: float = 360.0) -> Any:
    if angle <= 0 or angle > 360.0:
        raise KompasOperationError("Вращение: angle должен быть в диапазоне (0, 360]")
    type_id = O3D_BASE_ROTATED if part._feature_count == 0 else O3D_BOSS_ROTATED
    _log(f"revolve type_id={type_id} angle={angle}")
    try:
        entity = part._part.NewEntity(type_id)
        if entity is None:
            raise KompasOperationError(f"NewEntity({type_id}) вернул None")
        definition = entity.GetDefinition
        try:
            definition.SetSketch(sketch.entity)
        except Exception as exc:
            raise KompasOperationError(f"SetSketch (revolve): {exc}") from exc
        _set_rotated_side_param(definition, angle)
        result = entity.Create
        if not _created_ok(result):
            raise KompasOperationError(f"entity.Create failed for revolve: {result!r}")
        try:
            entity.Update
        except Exception as exc:
            _log(f"revolve Update skip: {exc}")
        return entity
    except KompasOperationError:
        raise
    except Exception as exc:
        raise KompasOperationError(f"Вращение: {exc}") from exc
