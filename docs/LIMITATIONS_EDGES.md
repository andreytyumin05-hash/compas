# Ограничения: рёбра, фаска, скругление

## Что реализовано

| API | Смысл |
|-----|--------|
| `part.get_edges("all")` | Собрать рёбра через `EntityCollection(o3d_edge*)` или `Face.EdgeCollection` |
| `parallel_x/y/z` | Фильтр по `direction` ребра, если COM отдал вектор |
| `near_point` / `top_z` / `bottom_z` | Фильтр по `midpoint`, если COM отдал координаты |
| `part.chamfer(edges, distance=…)` | NewEntity(chamfer) + attach edges + size |
| `part.fillet(edges, radius=…)` | NewEntity(fillet) + attach edges + radius |

Ошибки геометрии (слишком большой радиус и т.п.) поднимаются как `KompasOperationError` с текстом, не как сырой COM.

## Что может не работать на конкретной установке

1. **Пустой `get_edges("all")`**  
   Typelib не зарегистрирована / id `o3d_edge` другие / тело без solid.  
   → Сначала `extrude`, затем smoke; при необходимости править `_O3D_EDGE_CANDIDATES` в `core/edges.py`.

2. **`parallel_*`, `top_z`, `near_point`**  
   Нужны midpoint/direction с ребра. Late binding часто **не отдаёт** геометрию ребра → фильтр честно падает с просьбой использовать `"all"`.

3. **Привязка рёбер к fillet/chamfer definition**  
   Пути `AddArrayOfEdges` / `Edges.Add` / `ArrayOfEdges` перебираются. Если ни один не принят — ошибка «Не удалось привязать рёбра…». Это зависит от версии API5 definition, не от LLM.

4. **Скругление после сложных булевых**  
   Не тестировалось стабильно: пересечения, короткие рёбра, T-стыки часто отвергаются ядром КОМПАС даже из UI.

5. **Выбор «рёбра одной грани по нормали» / «пересечение двух граней»**  
   Заготовки фильтрации по face normal требуют надёжного чтения нормали грани из COM; пока **не** выставляются как обещанный API для LLM, чтобы не врать.

## Как проверить у себя

```powershell
git checkout agent-v2-vision
# КОМПАС открыт
python -m core.smoke_edges
python -m core.smoke_edges cube bushing plate
```

Лог stdout (число рёбер, OK/FAIL) — приложи к PR. Скриншоты КОМПАС — с твоей машины (CI без GUI КОМПАС не соберёт).

## Loft / sweep / boolean

В этой итерации **не** добавляются в публичный API агента (чтобы LLM/бот не обещали несуществующее). Отдельная задача после стабилизации рёбер.
