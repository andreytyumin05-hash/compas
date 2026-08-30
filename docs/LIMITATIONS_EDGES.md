# Рёбра / фаска / скругление (v23)

## Подтверждено на машине пользователя (smoke_edges 4/4)

- `EntityCollection(o3d_edge=7)` собирает рёбра
- `GetDefinition` — **property**, без `()`
- `definition.array().Add(edge)` + `Create` — fillet/chamfer работают
- `near_point` / `SelectByPoint` — работает (bushing: 1 ребро)

## API

```python
edges = part.get_edges("all")
part.fillet(edges, radius=2.0)
part.chamfer(edges, distance=1.5)
near = part.get_edges("near_point", point=(20, 0, 50))
```

Фильтры `parallel_*` / `top_z` без midpoint в late-binding **не** обещаем.

## Число рёбер

У «куба» в логе может быть >12 (вспомогательная топология КОМПАС) — не ошибка, если fillet OK.
