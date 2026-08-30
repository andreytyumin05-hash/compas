# CAD-паттерны (core)

## Дерево
эскиз → extrude/cut → следующий эскиз → …  
Отверстия только через `hole` / `cut`, не «круги в одном extrude с контуром».

## Размеры
| Текст | Код |
|-------|-----|
| Ø20 / D20 | `circle(..., 10)` или `hole(..., diameter=20)` |
| R5 | radius=5 |
| 100×60×8 | rectangle/rounded 100×60, depth=8 |
| n отв. на PCD | `pattern_holes_circular((0,0), pcd=…, count=n, diameter=…)` |

## Stadium / овал / «облонг» R=половина ширины
Не полигон. Только:
```python
sk.rounded_rect(-L/2, -W/2, L, W, radius=W/2)
# или
sk.stadium(-L/2, -W/2, L, W)
```
Пример крышка 116×80 t=13, R40, бобышка R30 h=18:
```python
from core import Part
part = Part.create("Крышка")
with part.sketch("xy") as sk:
    sk.rounded_rect(-58, -40, 116, 80, radius=40)
part.extrude(sk, depth=13)
with part.sketch("xy") as sk2:
    sk2.circle(0, 0, 30)
part.extrude(sk2, depth=18)
part.update()
```

## Втулка
circle R_out → extrude(L) → hole(diameter=D_in) или cut.

## Фланец
circle → extrude(t) → hole центр → pattern_holes_circular.

## Фаска / скругление рёбер
```python
edges = part.get_edges("all")
part.fillet(edges, radius=1.0)
part.chamfer(edges, distance=0.5)
```

## Не выдумывать
loft, sweep, boolean, win32com, произвольные имена методов.
