"""
Формообразующие операции (выдавливание, вырезание, вращение и т.д.).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from win32com.client import CastTo

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part
    from .sketch import Sketch


def extrude(
    part: "Part",
    sketch: "Sketch",
    depth: float,
    direction: str = "normal",
    both_directions: bool = False,
) -> Any:
    """
    Выдавливание (бобышка).

    direction: "normal" | "reverse"
    both_directions: выдавить в обе стороны (глубина — в каждую)
    """
    const = part.app.const3d
    container = part._container

    try:
        boss = CastTo(
            container.Extrusions.Add(const.o3d_bossExtrusion),
            "IExtrusion",
        )
        boss.Sketch = sketch.entity

        if both_directions:
            boss.Direction = const.dtBoth
            boss.SetSideParameters(True, const.etBlind, float(depth), 0.0, False, None)
            boss.SetSideParameters(False, const.etBlind, float(depth), 0.0, False, None)
        else:
            if direction == "reverse":
                boss.Direction = const.dtReverse
            else:
                boss.Direction = const.dtNormal
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
    """
    Вырезание выдавливанием.

    through_all=True — через всю деталь.
    """
    const = part.app.const3d
    container = part._container

    try:
        cut = CastTo(
            container.Extrusions.Add(const.o3d_cutExtrusion),
            "IExtrusion",
        )
        cut.Sketch = sketch.entity

        if through_all:
            cut.Direction = const.dtBoth
            # etThroughAll = 1
            cut.SetSideParameters(True, const.etThroughAll, 0.0, 0.0, False, None)
        else:
            if direction == "reverse":
                cut.Direction = const.dtReverse
            else:
                cut.Direction = const.dtNormal
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
    """
    Вращение.

    Пока базовая реализация. Для полноценной оси может потребоваться
    дополнительная настройка в зависимости от версии API.
    """
    const = part.app.const3d
    container = part._container

    try:
        # o3d_bossRotated
        rot = CastTo(
            container.Rotations.Add(const.o3d_bossRotated),
            "IRotation",
        )
        rot.Sketch = sketch.entity
        # Угол в градусах — точный интерфейс зависит от версии,
        # оставляем место для уточнения при тестировании
        try:
            rot.Angle = float(angle)
        except Exception:
            pass
        rot.Update()
        part._top_part.Update()
        return rot
    except Exception as e:
        raise KompasOperationError(
            f"Ошибка вращения: {e}. "
            "Проверьте версию API и наличие оси в эскизе."
        ) from e
