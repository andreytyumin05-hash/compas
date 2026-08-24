# Что сделать сейчас

## Ситуация

- КОМПАС COM — **OK**
- Ключ Groq — **работает** (usage растёт)
- Модели `llama-3.1-8b-instant` и `llama-3.3-70b-versatile` — **нет доступа** (404)

## Шаги

```powershell
git pull origin dev

# 1) Посмотреть, какие модели реально доступны твоему ключу
python -m agent.list_models
```

В выводе будет список. Возьми **любую chat-модель** (не whisper, не guard) и пропиши в `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=твой_ключ
LLM_MODEL=сюда_id_из_списка
```

Потом:

```powershell
python -m agent.runner "Втулка: наружный диаметр 40, внутренний 20, длина 50"
```

## Если list_models пустой

Значит у ключа странные ограничения. Тогда проще перейти на **Gemini** (бесплатно):

1. Ключ: https://aistudio.google.com
2. В `.env`:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=твой_ключ
LLM_MODEL=gemini-2.0-flash
```

И снова `python -m agent.runner "..."`.

Пришли вывод `list_models` или новый `responce.txt`.
