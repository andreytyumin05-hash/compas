# Память паттернов CAD (core)

## Порядок
1) Базовое тело (extrude) 2) Бобышки / ступени (ещё extrude) 3) Глухие карманы / pockets (cut depth=...) 4) Отверстия / pattern_holes 5) fillet/chamfer

## Сложная крышка / flange
Для сложной крышки задаётся последовательность: базовый контур → extrude(base) → boss(центральный круг/оболочка) → blind pocket или вырез на заданную глубину → отверстия по PCD/матрице. Не делать все операции в одном эскизе; иначе KOMPAS не группирует корректно.

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
