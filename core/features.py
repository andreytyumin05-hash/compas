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


def pattern_holes_points(
    part: "Part",
    points: Sequence[Tuple[float, float]],
    diameter: float,
    *,
    through_all: bool = True,
    depth: float = 0.0,
    plane: str = "xy",
) -> None:
    """Отверстия по списку произвольных координат на плоскости."""
    if not points:
        raise KompasOperationError("pattern_holes_points: points is empty")
    if diameter <= 0:
        raise KompasOperationError("pattern_holes_points: diameter > 0")
    r = float(diameter) / 2.0
    with part.sketch(plane) as sk:
        for x, y in points:
            sk.circle(float(x), float(y), r)
    if through_all:
        part.cut(sk, through_all=True)
    else:
        part.cut(sk, depth=float(depth), through_all=False)


def hole_list(
    part: "Part",
    points: Sequence[Tuple[float, float]],
    diameters: float | Sequence[float],
    *,
    through_all: bool = True,
    depth: float = 0.0,
    plane: str = "xy",
) -> None:
    """Несколько отверстий с возможностью задавать разные диаметры."""
    pts = list(points)
    if not pts:
        raise KompasOperationError("hole_list: points is empty")

    if isinstance(diameters, (int, float)):
        d_list = [float(diameters)] * len(pts)
    else:
        d_list = [float(d) for d in diameters]
        if len(d_list) != len(pts):
            raise KompasOperationError(
                "hole_list: количество диаметров должно совпадать с количеством точек"
            )

    for (x, y), d in zip(pts, d_list):
        part.hole(x, y, d, depth=depth, through_all=through_all, plane=plane)


def pattern_holes_linear(
    part: "Part",
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
    """Линейный массив отверстий."""
    if count < 1:
        raise KompasOperationError("pattern_holes_linear: count >= 1")
    if step == 0:
        raise KompasOperationError("pattern_holes_linear: step != 0")
    dx, dy = direction
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    ox, oy = start
    pts = [(ox + i * step * ux, oy + i * step * uy) for i in range(count)]
    pattern_holes_points(
        part,
        pts,
        diameter,
        through_all=through_all,
        depth=depth,
        plane=plane,
    )


def boss(
    part: "Part",
    x: float,
    y: float,
    diameter: float,
    height: float,
    *,
    plane: str = "xy",
) -> None:
    """Бобышка/выступ кругового сечения на плоскости."""
    if diameter <= 0:
        raise KompasOperationError("boss: diameter > 0")
    if height <= 0:
        raise KompasOperationError("boss: height > 0")
    with part.sketch(plane) as sk:
        sk.circle(float(x), float(y), float(diameter) / 2.0)
    part.extrude(sk, depth=float(height))


def hex_boss(
    part: "Part",
    x: float,
    y: float,
    diameter: float,
    height: float,
    *,
    plane: str = "xy",
) -> None:
    """Шестигранная бобышка/головка под ключ."""
    if diameter <= 0:
        raise KompasOperationError("hex_boss: diameter > 0")
    if height <= 0:
        raise KompasOperationError("hex_boss: height > 0")
    r = float(diameter) / 2.0
    pts = []
    for i in range(6):
        ang = math.radians(30 + 60 * i)
        pts.append((float(x) + r * math.cos(ang), float(y) + r * math.sin(ang)))
    with part.sketch(plane) as sk:
        sk.polygon(pts, closed=True)
    part.extrude(sk, depth=float(height))


def ring_groove(
    part: "Part",
    x: float,
    y: float,
    outer_diameter: float,
    inner_diameter: float,
    depth: float,
    *,
    plane: str = "xy",
) -> None:
    """Кольцевая канавка: концентрический annulus cut."""
    if outer_diameter <= 0 or inner_diameter <= 0:
        raise KompasOperationError("ring_groove: диаметры > 0")
    if outer_diameter <= inner_diameter:
        raise KompasOperationError("ring_groove: outer_diameter > inner_diameter")
    if depth <= 0:
        raise KompasOperationError("ring_groove: depth > 0")
    with part.sketch(plane) as sk:
        sk.circle(float(x), float(y), float(outer_diameter) / 2.0)
        sk.circle(float(x), float(y), float(inner_diameter) / 2.0)
    part.cut(sk, depth=float(depth), through_all=False)


def keyway(
    part: "Part",
    x: float,
    y: float,
    length: float,
    width: float,
    depth: float,
    *,
    axis: str = "x",
    plane: str = "xy",
) -> None:
    """Шпоночный паз в середине вала/ступени. Параллелен оси X или Y."""
    if length <= 0 or width <= 0 or depth <= 0:
        raise KompasOperationError("keyway: length/width/depth > 0")
    if axis.lower() not in {"x", "y"}:
        raise KompasOperationError("keyway: axis in {'x', 'y'}")
    if axis.lower() == "x":
        px1, py1 = float(x) - float(length) / 2.0, float(y)
        px2, py2 = float(x) + float(length) / 2.0, float(y)
    else:
        px1, py1 = float(x), float(y) - float(length) / 2.0
        px2, py2 = float(x), float(y) + float(length) / 2.0
    with part.sketch(plane) as sk:
        sk.slot(px1, py1, px2, py2, float(width))
    part.cut(sk, depth=float(depth), through_all=False)


def pocket(
    part: "Part",
    x: float,
    y: float,
    diameter: float,
    depth: float,
    *,
    plane: str = "xy",
) -> None:
    """Глухой карман кругового сечения."""
    if diameter <= 0:
        raise KompasOperationError("pocket: diameter > 0")
    if depth <= 0:
        raise KompasOperationError("pocket: depth > 0")
    with part.sketch(plane) as sk:
        sk.circle(float(x), float(y), float(diameter) / 2.0)
    part.cut(sk, depth=float(depth), through_all=False)


def counterbore(
    part: "Part",
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
    """Базовое ступенчатое отверстие: основной диаметр + цековка."""
    if pilot_diameter <= 0 or counterbore_diameter <= 0:
        raise KompasOperationError("counterbore: диаметры > 0")
    if counterbore_depth <= 0:
        raise KompasOperationError("counterbore: counterbore_depth > 0")
    if not through_all and pilot_depth <= 0:
        raise KompasOperationError("counterbore: pilot_depth > 0 для blind отверстия")

    if through_all:
        part.hole(x, y, pilot_diameter, through_all=True, plane=plane)
    else:
        part.hole(x, y, pilot_diameter, depth=pilot_depth, through_all=False, plane=plane)

    with part.sketch(plane) as sk:
        sk.circle(float(x), float(y), float(counterbore_diameter) / 2.0)
    part.cut(sk, depth=float(counterbore_depth), through_all=False)


def countersink(
    part: "Part",
    x: float,
    y: float,
    pilot_diameter: float,
    countersink_diameter: float,
    depth: float,
    *,
    angle_deg: float = 90.0,
    plane: str = "xy",
) -> None:
    """Упрощённая зенковка для текущей архитектуры: расширенный blind cut на верхней плоскости.

    Настоящая коническая зенковка (трапеция / конус) требует отдельной поддержки в COM
    для tapered cut, которой в текущем core нет. Здесь создаётся реальный blind-выбор
    увеличенного диаметра, что достаточно для большинства simple countersink cases.
    """
    if pilot_diameter <= 0 or countersink_diameter <= 0:
        raise KompasOperationError("countersink: диаметры > 0")
    if depth <= 0:
        raise KompasOperationError("countersink: depth > 0")
    if not (0 < angle_deg < 180):
        raise KompasOperationError("countersink: angle_deg должен быть между 0 и 180")
    part.hole(x, y, pilot_diameter, depth=depth, through_all=False, plane=plane)
    with part.sketch(plane) as sk:
        sk.circle(float(x), float(y), float(countersink_diameter) / 2.0)
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


def mirror_points(
    points: Sequence[Tuple[float, float]],
    *,
    axis: str = "x",
) -> List[Tuple[float, float]]:
    """Отразить набор точек относительно оси X или Y."""
    if not points:
        return []
    axis_key = axis.lower().strip()
    if axis_key not in {"x", "y"}:
        raise KompasOperationError("mirror_points: axis in {'x', 'y'}")
    mirrored: List[Tuple[float, float]] = []
    for px, py in points:
        if axis_key == "x":
            mirrored.append((-px, py))
        else:
            mirrored.append((px, -py))
    return mirrored


def slot(
    part: "Part",
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
    """Паз по линейному сегменту с шириной width."""
    if width <= 0:
        raise KompasOperationError("slot: width > 0")
    if not through_all and depth <= 0:
        raise KompasOperationError("slot: blind depth > 0")
    with part.sketch(plane) as sk:
        sk.slot(float(x1), float(y1), float(x2), float(y2), float(width))
    if through_all:
        part.cut(sk, through_all=True)
    else:
        part.cut(sk, depth=float(depth), through_all=False)


def step(
    part: "Part",
    x: float,
    y: float,
    width: float,
    height: float,
    depth: float,
    *,
    shape: str = "rect",
    plane: str = "xy",
) -> None:
    """Простой уступ/ступень как отдельная boss-операция."""
    if width <= 0 or height <= 0 or depth <= 0:
        raise KompasOperationError("step: width/height/depth > 0")
    shape_key = shape.lower().strip()
    with part.sketch(plane) as sk:
        if shape_key == "circle":
            sk.circle(float(x), float(y), float(width) / 2.0)
        elif shape_key == "rect":
            sk.rectangle(float(x) - float(width) / 2.0, float(y) - float(height) / 2.0, float(width), float(height))
        else:
            raise KompasOperationError("step: shape in {'rect', 'circle'}")
    part.extrude(sk, depth=float(depth))
