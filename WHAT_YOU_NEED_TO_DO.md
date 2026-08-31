# Пока тебя нет

```powershell
git pull origin agent-v2-vision

# офлайн
python -m agent.dry_run --self-test

# GUI (КОМПАС открыт)
python -m desktop.app

# бот
python -m bot
```

Новое:
- `sk.dim_linear` / `sk.dim_radial` — попытка размеров в эскизе (может быть False)
- `desktop/` — простое окно + «Проверить обновления» → GitHub
- `ROADMAP.md`, `docs/PARAMETRIC_SKETCH.md`, `VERSION`

Обновлять приложение: **git pull**, не ждать «магический exe».
