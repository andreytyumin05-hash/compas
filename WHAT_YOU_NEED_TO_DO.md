# Что делать

## Ветки

| Ветка | Назначение |
|-------|------------|
| **agent-v2** | Рабочая (актуальный код) |
| **main** | Старый merge MVP — подтянуть позже с agent-v2 |

Удали локально лишнее:
```powershell
git fetch --prune
git checkout agent-v2
git pull origin agent-v2

# удалить чужие ветки на GitHub (если ещё есть):
# git push origin --delete dev
# git push origin --delete features/advanced
```

## Окружение

- Windows, КОМПАС-3D, Python 64-bit, venv, `pip install -r requirements.txt`
- `.env` с ключом LLM (`GROQ_API_KEY` / `GEMINI_API_KEY` и `LLM_MODEL`)

## Команды

```powershell
# КОМПАС открыт
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"

# только код
python -m agent.runner "Плита 100x60x8, 4 отверстия диаметр 9 по углам отступ 10"

# диагностика COM
python -m core.diagnose
```

## Дальше по смыслу

1. Гонять разные текстовые задачи через `agent.build`
2. Если ошибка COM — текст в issue / чат (файл responce.txt в git не кладём)
3. Фаски/скругления — экспериментально (`chamfer`/`fillet`)
4. Когда стабильно — смержить agent-v2 → main
