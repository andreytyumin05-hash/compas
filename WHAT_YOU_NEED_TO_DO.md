# Проверка агентов (01.09.2026)

Исправлено: строка «Порядок: … карманы … отверстия … фаски» в ТЗ **ложно** требовала pocket/hole/chamfer даже для простой плиты.

Теперь:
- `ops_order=base,add_material,...` без триггер-слов
- `required_features=` / `feature=` — главный источник требований
- канавка (`feature=groove`) проверяется

```powershell
git pull origin agent-v2-vision
python -m agent.dry_run --self-test
python -m unittest tests.test_offline_dry_run tests.test_feature_false_positives tests.test_task_feature_requirements tests.test_agent_templates -v
```
