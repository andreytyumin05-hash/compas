# Visual Fluent v2 — уже на GitHub

Ветка: **feature/visual-fluent-v2**

```powershell
git fetch origin
git checkout feature/visual-fluent-v2
git pull origin feature/visual-fluent-v2

python -m unittest tests.test_visual_and_vars tests.test_offline_dry_run -v

# live
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

На remote:
- `core/visual.py`, `core/part_fluent.py`
- `Part` получает Fluent через `core/__init__.py`
- `critic_warnings`, prompts, runner soft-warn
- тесты `tests/test_visual_and_vars.py`
- `docs/VISUAL_FLUENT_V2.md`

UI/бот не трогали.
