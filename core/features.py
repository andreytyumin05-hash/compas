"""Высокоуровневые фичи поверх sketch/extrude/cut.

Example — сквозное отверстие в центре:
    part.hole(0, 0, diameter=10, through_all=True)

Example — 4 отверстия по углам плиты 100x60, отступ 10:
    part.pattern_holes_rect(10, 10, 90, 50, diameter=9)
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING, List, Sequence, Tuple

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part


def hole(
    part: "Part",
    x: float,
    y: float,
    diameter: float,
    *,
    depth: float = 0.0,
    through_all: bool = True,
    plane: str = "xy",
) -> None:
    """
    Цилиндрическое отверстие (эскиз circle + cut).

    Args:
        x, y: центр на плоскости эскиза (мм)
        diameter: диаметр (мм), должен быть > 0
        through_all: сквозное; иначе cut на depth
        depth: глубина blind-отверстия (мм)

    Example:
        part.hole(0, 0, diameter=10, through_all=True)
        part.hole(20, 0, diameter=6, depth=8, through_all=False)
    """
    if diameter <= 0:
        raise KompasOperationError(f"hole: diameter должен быть > 0, получено {diameter}")
    if not through_all and depth <= 0:
        raise KompasOperationError("hole: для blind нужен depth > 0")

    r = float(diameter) / 2.0
    with part.sketch(plane) as sk:
        sk.circle(float(x), float(y), r)
    if through_all:
        part.cut(sk, through_all=True)
    else:
        part.cut(sk, depth=float(depth), through_all=False)


def pattern_holes_circular(
    part: "Part",
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
    """
    Круговой массив отверстий на диаметре PCD.

    Example:
        # 4 отверстия Ø9 на диаметре 55
        part.pattern_holes_circular((0, 0), pcd=55, count=4, diameter=9)
    """
    if count < 1:
        raise KompasOperationError("pattern_holes_circular: count >= 1")
    if pcd <= 0 or diameter <= 0:
        raise KompasOperationError("pattern_holes_circular: pcd и diameter > 0")

    r_place = float(pcd) / 2.0
    r_hole = float(diameter) / 2.0
    cx, cy = center
    with part.sketch(plane) as sk:
        for i in range(count):
            ang = math.radians(start_angle_deg + 360.0 * i / count)
            sk.circle(cx + r_place * math.cos(ang), cy + r_place * math.sin(ang), r_hole)
    if through_all:
        part.cut(sk, through_all=True)
    else:
        part.cut(sk, depth=float(depth), through_all=False)


def pattern_holes_rect(
    part: "Part",
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
    """
    Четыре отверстия в углах прямоугольника (x1,y1)–(x2,y2).

    Example:
        part.pattern_holes_rect(10, 10, 90, 50, diameter=9)
    """
    if diameter <= 0:
        raise KompasOperationError("pattern_holes_rect: diameter > 0")
    r = float(diameter) / 2.0
    pts = [(x1, y1), (x2, y1), (x1, y2), (x2, y2)]
    with part.sketch(plane) as sk:
        for x, y in pts:
            sk.circle(float(x), float(y), r)
    if through_all:
        part.cut(sk, through_all=True)
    else:
        part.cut(sk, depth=float(depth), through_all=False)


def pattern_linear_points(
    origin: Tuple[float, float],
    count: int,
    step: float,
    direction: Tuple[float, float] = (1.0, 0.0),
) -> List[Tuple[float, float]]:
    """Координаты для линейного массива точек (helper для эскиза)."""
    if count < 1:
        raise KompasOperationError("pattern_linear_points: count >= 1")
    dx, dy = direction
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    ox, oy = origin
    return [(ox + i * step * ux, oy + i * step * uy) for i in range(count)]
