# .env — что должно быть

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile

GEMINI_API_KEY=AIza...
VISION_PROVIDER=gemini
VISION_MODEL=gemini-2.0-flash

TELEGRAM_BOT_TOKEN=123:ABC...
```

**Нельзя** ставить `VISION_MODEL=qwen/...` или брать `LLM_MODEL` для Gemini — будет `unexpected model name format`.

`OPENROUTER_API_KEY` **не нужен**, если есть рабочий Gemini.

## Почему упал vision
Код подставлял `LLM_MODEL=qwen/qwen3.6-27b` в Gemini. Исправлено: для картинок только `VISION_MODEL` с `gemini` в имени, иначе `gemini-2.0-flash`.

## Безопасность
В answers/логах засветился **токен Telegram-бота**. В @BotFather сделай **Revoke** и запиши новый в `.env`. Не коммить `.env` и не клади токены в `answers.txt`.

## Проверка
```powershell
git pull origin agent-v2-vision
# поправь .env как выше
python -m bot
```
- «привет» → подсказка, не сборка
- фото → распознавание без ошибки model name
