# CAD patterns (агент)

## Крышка / фланец stadium (как image.png)

Типичный BUILD_PLAN:
1. База: `sk.stadium(x, y, L, W)` + `extrude(depth=толщина_фланца)` — НЕ rectangle.
2. Бобышка: второй `stadium` меньшего размера + `extrude(height_boss)`.
3. Центральные отверстия: `hole` по координатам (например два Ø28, шаг 36 → x=±18).
4. Крепёж с цековкой: `counterbore(x,y, pilot_diameter=7, counterbore_diameter=11, counterbore_depth=6, through_all=True)` × N.
5. Штифты: `hole` или `pattern_holes_points` Ø5.
6. Виды: `set_view("top")` затем `iso` + screenshot.

Координаты stadium: **левый нижний угол** (x, y), length вдоль X, width вдоль Y.
Радиус торцов stadium = width/2 (авто в API).

## Втулка

circle(R_нар) extrude L + hole(d_вн) through_all.

## Запреты

- Одна rectangle-плита вместо stadium-крышки.
- Игнор цековок (только hole 7 без counterbore).
- Скрин только сбоку — отверстия не видны.
