# compas — ИИ → КОМПАС-3D

Текст → Python (`core`) → модель в КОМПАС-3D (Windows, COM).

## Быстрый старт

```powershell
git checkout agent-v2
git pull origin agent-v2
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# прописать API-ключ и LLM_MODEL
```

```powershell
# КОМПАС запущен
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
```

## Структура

```
core/     # COM-обёртка (Part, sketch, extrude, cut)
agent/    # LLM → код → build
```

Подробности: `WHAT_YOU_NEED_TO_DO.md`.
