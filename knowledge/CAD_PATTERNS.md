# Дерево построения (сложная деталь)

1. **База** — контур + `extrude`
2. **Ступени / бобышки** — новый sketch + `extrude` (не в том же эскизе, что вырез)
3. **Карманы** — sketch + `cut(depth=…)` глухой; сквозное — `through_all=True`
4. **Отверстия** — `hole` / `pattern_holes_*`
5. **Зенковка** — сначала мелкий вырез/hole большего Ø, потом основной hole
6. **Кромки** — `fillet` / `chamfer` в конце

Плоскости: `sketch("xy"|"xz"|"yz")`.

Stadium: `rounded_rect` / `stadium`, не ломаная.
Ø → радиус = D/2 для circle, diameter= для hole.
