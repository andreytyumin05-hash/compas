# Память паттернов CAD (core)

## Порядок
1) Базовое тело (extrude) 2) Бобышки (ещё extrude) 3) Вырезы/hole 4) fillet/chamfer

## Диаметры
Текст ØD / D20 → `circle(..., D/2)` или `hole(..., diameter=D)`.

## Stadium / облонг
`sk.rounded_rect(-L/2, -W/2, L, W, radius=min(L,W)/2)` или `sk.stadium(...)`.
Не polygon.

## Втулка
Наружный круг → extrude(L) → hole(внутренний).

## Фланец круглый
circle → extrude(t) → hole центр → pattern_holes_circular(pcd, count, diameter).

## Плита
rectangle → extrude → pattern_holes_rect или hole в углах.

## Ошибки v23
- Не ksArcByPoint; только ksArcByAngle (уже в core).
- Не нулевые линии при R=W/2.
- GetDefinition / BeginEdit без ().
