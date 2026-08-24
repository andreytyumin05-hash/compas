"""
Формообразующие операции (late binding).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .comutil import safe_cast
from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part
    from .sketch import Sketch


def _get_extrusions(container: Any) -> Any:
    ext = getattr(container, "Extrusions", None)
    if ext is None:
        raise KompasOperationError("У детали нет коллекции Extrusions")
    return ext


def extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float,
    direction: str = "normal",
    both_directions: bool = False,
) -> Any:
    const = part.app.const3d
    container = part._container

    try:
        extrusions = _get_extrusions(container)
        boss = extrusions.Add(const.o3d_bossExtrusion)
        boss = safe_cast(boss, "IExtrusion")
        boss.Sketch = sketch.entity

        if both_directions:
            boss.Direction = const.dtBoth
            boss.SetSideParameters(True, const.etBlind, float(depth), 0.0, False, None)
            boss.SetSideParameters(False, const.etBlind, float(depth), 0.0, False, None)
        else:
            boss.Direction = (
                const.dtReverse if direction == "reverse" else const.dtNormal
            )
            boss.SetSideParameters(True, const.etBlind, float(depth), 0.0, False, None)

        boss.Update()
        part._top_part.Update()
        return boss
    except Exception as e:
        raise KompasOperationError(f"Ошибка выдавливания: {e}") from e


def cut_extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float = 0.0,
    through_all: bool = False,
    direction: str = "normal",
) -> Any:
    const = part.app.const3d
    container = part._container

    try:
        extrusions = _get_extrusions(container)
        cut = extrusions.Add(const.o3d_cutExtrusion)
        cut = safe_cast(cut, "IExtrusion")
        cut.Sketch = sketch.entity

        if through_all:
            cut.Direction = const.dtBoth
            cut.SetSideParameters(True, const.etThroughAll, 0.0, 0.0, False, None)
        else:
            cut.Direction = (
                const.dtReverse if direction == "reverse" else const.dtNormal
            )
            cut.SetSideParameters(True, const.etBlind, float(depth), 0.0, False, None)

        cut.Update()
        part._top_part.Update()
        return cut
    except Exception as e:
        raise KompasOperationError(f"Ошибка вырезания: {e}") from e


def revolve(
    part: "Part",
    sketch: "Sketch",
    angle: float = 360.0,
    axis_point1: Optional[tuple] = None,
    axis_point2: Optional[tuple] = None,
) -> Any:
    const = part.app.const3d
    container = part._container

    try:
        rotations = getattr(container, "Rotations", None)
        if rotations is None:
            raise KompasOperationError("Нет коллекции Rotations")
        rot = rotations.Add(const.o3d_bossRotated)
        rot = safe_cast(rot, "IRotation")
        rot.Sketch = sketch.entity
        try:
            rot.Angle = float(angle)
        except Exception:
            pass
        rot.Update()
        part._top_part.Update()
        return rot
    except Exception as e:
        raise KompasOperationError(f"Ошибка вращения: {e}") from e
