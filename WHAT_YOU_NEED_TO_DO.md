# Сейчас

```powershell
git pull origin agent-v2-vision
python -m core.smoke_rounded
```

Если FAIL — открой в VS Code файл **`CODEX_CHECKLIST.md`** и отдай его локальному агенту (Codex): там расписано, что проверить и как чинить `ksArc*` на КОМПАС v23.

Ручной фикс тоже там: `core/sketch.py` → direction у дуги.
