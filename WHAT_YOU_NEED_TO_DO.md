# agent-v2-vision — итерация 2 (рёбра)

```powershell
git fetch
git checkout agent-v2-vision
git pull origin agent-v2-vision
```

## Задача 1 — что проверить тебе

КОМПАС открыт:

```powershell
python -m core.smoke_edges
python -m core.smoke_edges cube
python -m core.smoke_edges bushing
python -m core.smoke_edges plate
```

Ожидание в логе: `edges collected: N` (N>0), затем `OK` или понятный `KompasOperationError`.

Пришли в чат **полный stdout** тестов. Скриншоты моделей — по возможности.

## API для кода/LLM

```python
edges = part.get_edges("all")
part.fillet(edges, radius=1.0)
part.chamfer(edges, distance=0.5)
```

См. `docs/LIMITATIONS_EDGES.md` — что может не взлететь на твоей версии COM.

## Ещё не делали в этой итерации

Задачи 2–5 (loft, native m3d/cdw, cleanup документа, кнопки форматов) — **после** подтверждения smoke_edges.
