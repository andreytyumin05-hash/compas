# Фикс крышки + бот

```powershell
git pull origin feature/visual-fluent-v2

# VLM по умолчанию ВЫКЛ (не виснет 7 мин). Включить:
# $env:COMPAS_VISUAL_LOOP="1"

python -m bot
```

Фото крышки: vision план → код обязан stadium + 2×extrude + hole/counterbore.
Скрины: **top + iso** (не side).

Проверка offline:
```powershell
python -m agent.dry_run --task "Крышка stadium 116x80 толщина 13 бобышка цековка 6x" --code-file ...
```
