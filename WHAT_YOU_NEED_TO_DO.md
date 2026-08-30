# Что сделать сейчас (после фикса рёбер)

```powershell
git checkout agent-v2-vision
git pull origin agent-v2-vision
```

## Что было не так (по твоему answers)

1. Рёбра брались из `EntityCollection(8)` — это **вершины** (`o3d_vertex`), не рёбра. Нужен **`o3d_edge = 7`**.
2. Привязка шла через несуществующие `AddArrayOfEdges` — в API5 нужно **`definition.array().Clear()` + `array.Add(edge)`**.
3. Размер фаски — через **`SetChamferParam(True, d, d)`**, не только `length1`.

## Проверка

КОМПАС открыт:

```powershell
python -m core.smoke_edges
```

Ждём в логе:
- `edge[i] src=EntityCollection(7)` (не 8)
- для куба число рёбер около **12** (не 20)
- `OK: cube` / `chamfer` / …

Полный stdout снова положи в `answers.txt` и закоммить/напиши в чат.

Если снова FAIL — пришли лог; следующий шаг: диагностика методов `definition` (dir) на живом объекте.
