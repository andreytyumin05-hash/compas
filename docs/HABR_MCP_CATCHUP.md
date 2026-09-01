# Catch-up: Habr AI-агент + KOMPAS-3D-MCP

## Уже в feature/visual-fluent-v2

| Фишка | Где |
|-------|-----|
| Python-обёртка над COM (не сырой COM) | `core/` |
| `part.var` / `set_properties` / `set_view` / `screenshot` | `core/visual.py`, `part_fluent` |
| Soft critic: нет var / props / visual | `agent/validate.critic_warnings` |
| Soft → runner repair + лог | `agent/runner.py` |
| Offline verify + route hint | `agent/verify.py`, `dry_run` |
| Промпт: visual loop ≥2 вида | `agent/prompts.py` |
| `part.verify()` после build | `part_fluent.verify` |

## Ещё не live (нужна отладка на твоей v23)

- Реальные управляющие переменные КОМПАС (не только Python-контекст)
- VLM-критик по скриншотам (сейчас скриншот пишется, анализ — вручную / следующий шаг)
- Отдельный drawing2model pipeline (статья: сквозной ReAct ~0.25 на средних)
- stale-ref после rebuild (документировано в verify, код-guard позже)

## Как гонять

```powershell
git checkout feature/visual-fluent-v2
git pull
python -m agent.dry_run --self-test
python -m unittest tests.test_visual_and_vars -v
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
# в коде смотри var / set_properties / screenshot
```

## Takeaway из статьи

Один блок нормального кода + visual control > десяток атомарных tools.  
Параметрическое дерево важнее «мёртвого» STEP.
