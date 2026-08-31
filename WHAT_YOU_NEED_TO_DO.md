# Офлайн-проверка (без КОМПАС)

```powershell
git pull origin agent-v2-vision

# встроенные кейсы
python -m agent.dry_run --self-test

# свой код
python -m agent.dry_run --task "Пробка Ø50 Ø30" --code-file script.py

# unit-тесты без КОМПАС
python -m unittest tests.test_offline_dry_run tests.test_agent_templates tests.test_task_feature_requirements -v
```

Исправлено: critic больше не запрещает `part.step` / `part.slot` (они есть в core).
