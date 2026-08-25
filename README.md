# compas — ИИ-агент для КОМПАС-3D

Генерация 3D-деталей в КОМПАС-3D по текстовому описанию через обёртку `core` + LLM (Groq / Gemini / OpenRouter).

| Ветка | Назначение |
|-------|------------|
| `dev` | Рабочая стабильная |
| `agent-v2` | Усиленный промпт, валидация, автозапуск `build` |
| `main` | Не использовать для разработки |

## Быстрый старт

```powershell
git checkout agent-v2
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# пропиши GROQ_API_KEY и LLM_MODEL=qwen/qwen3.6-27b
```

```powershell
python -m agent.list_models
python -m agent.runner "Втулка наружный 40 внутренний 20 длина 50"
python -m agent.build  "Втулка наружный 40 внутренний 20 длина 50"
```

`build` = генерация + выполнение в КОМПАС (нужен Windows + установленный КОМПАС-3D).

## Структура

```
core/           # COM-обёртка (Part, sketch, extrude, cut)
agent/
  prompts.py    # системный промпт
  validate.py   # проверка, что код не выдумал чужой API
  runner.py     # только генерация
  build.py      # генерация + exec в КОМПАС
  llm.py        # Groq / Gemini / OpenRouter
  list_models.py
```

## API `core` (кратко)

```python
from core import Part
part = Part.create("Деталь")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)      # радиус!
part.extrude(sk, depth=50)
with part.sketch("xy") as sk2:
    sk2.circle(0, 0, 10)
part.cut(sk2, through_all=True)
```

Подробности и ограничения — в `WHAT_YOU_NEED_TO_DO.md`.
