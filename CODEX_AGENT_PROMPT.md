# Промпт для локального агента VS Code (Codex)

Скопируй в чат агента целиком:

---

Ты работаешь в репозитории **compas**, ветка **agent-v2-vision** (не main).
Windows, КОМПАС-3D v23 открыт, venv активирован.

## Цель
Улучшить **качество генерации 3D-деталей**: меньше путаницы LLM, больше шаблонов, стабильный COM.

## Уже сделано upstream
- `rounded_rect` / stadium через ksArcByAngle, skip zero lines
- cascade LLM, templates, memory (`.compas_tmp/build_memory.jsonl`)
- vision → `spec_to_task_text` с key=value для templates

## Твои задачи
1. Прогони:
   ```
   python -m core.smoke_rounded
   python -m agent.build "Крышка length=116 width=80 thickness=13 outer_radius=40 boss_height=18 inner_radius=30"
   python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
   python -m agent.runner "Плита 100x60 толщина 8 отверстия 9 на углах отступ 10"
   ```
2. Если шаблон не сработал на «Плита…» — расширь `agent/templates.py`.
3. Если LLM даёт прозу/синтаксис — усили `agent/prompts.py` few-shot, не раздувай system.
4. Проверь `python -m bot` старт без traceback; queue stop без RuntimeWarning.
5. Удали мусор в корне: не коммить answers.txt, conflict markers, `__pycache__`.
6. Не трогай main; коммить в agent-v2-vision.

## Критерий готово
Три команды build/runner выше → валидный код + модель в КОМПАС без ручного правления.

---
