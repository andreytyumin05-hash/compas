"""
Выдавливание / вырезание — API5 NewEntity + SetSideParam + SetSketch + Create.
"""

from __future__ import annotations

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


def _set_side_param(definition: Any, through_all: bool, depth: float, direction: int) -> None:
    """
    Разные версии API принимают разную сигнатуру SetSideParam.
    Пробуем несколько вариантов.
    """
    et = ET_THROUGH_ALL if through_all else ET_BLIND
    d = 0.0 if through_all else float(depth)

    attempts = [
        # (bool side1, endType, depth, draft, bool unknown) — частый вариант из примеров
        lambda: definition.SetSideParam(True, et, d, 0, True),
        lambda: definition.SetSideParam(True, et, d, 0.0, False),
        lambda: definition.SetSideParam(True, et, d),
        # API7-подобная
        lambda: definition.SetSideParameters(True, et, d, 0.0, False, None),
    ]

    last_err = None
    for fn in attempts:
        try:
            fn()
            # направление
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
            continue

    # Последняя попытка через ExtrusionParam только
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
        return
    except Exception as e:
        raise KompasOperationError(
            f"Не удалось задать параметры выдавливания. Last: {last_err}; ExtrusionParam: {e}"
        ) from e


def extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float,
    direction: str = "normal",
    both_directions: bool = False,
) -> Any:
    # Первая операция — baseExtrusion, дальше bossExtrusion
    type_id = O3D_BASE_EXTRUSION if part._feature_count == 0 else O3D_BOSS_EXTRUSION
    dir_id = DT_BOTH if both_directions else (DT_REVERSE if direction == "reverse" else DT_NORMAL)

    try:
        entity = part._part.NewEntity(type_id)
        if entity is None:
            raise KompasOperationError(f"NewEntity({type_id}) вернул None")

        definition = entity.GetDefinition()
        _set_side_param(definition, through_all=False, depth=depth, direction=dir_id)

        try:
            definition.SetThinParam(False, DT_NORMAL, 0, 0)
        except Exception:
            pass

        try:
            definition.SetSketch(sketch.entity)
        except Exception as e:
            raise KompasOperationError(f"SetSketch: {e}") from e

        ok = entity.Create()
        if ok is False:
            raise KompasOperationError("entity.Create() вернул False (выдавливание)")

        try:
            entity.Update()
        except Exception:
            pass

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

    try:
        entity = part._part.NewEntity(type_id)
        if entity is None:
            raise KompasOperationError("NewEntity(cutExtrusion) вернул None")

        definition = entity.GetDefinition()
        _set_side_param(definition, through_all=through_all, depth=depth, direction=dir_id)

        try:
            definition.SetThinParam(False, DT_NORMAL, 0, 0)
        except Exception:
            pass

        try:
            definition.SetSketch(sketch.entity)
        except Exception as e:
            raise KompasOperationError(f"SetSketch (cut): {e}") from e

        ok = entity.Create()
        if ok is False:
            raise KompasOperationError("entity.Create() вернул False (вырезание)")

        try:
            entity.Update()
        except Exception:
            pass

        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Вырезание: {e}") from e


def revolve(part: "Part", sketch: "Sketch", angle: float = 360.0) -> Any:
    try:
        entity = part._part.NewEntity(O3D_BOSS_ROTATED)
        definition = entity.GetDefinition()
        try:
            definition.SetSketch(sketch.entity)
        except Exception as e:
            raise KompasOperationError(f"SetSketch (revolve): {e}") from e
        try:
            definition.angle = float(angle)
        except Exception:
            pass
        entity.Create()
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Вращение: {e}") from e
