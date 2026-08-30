# Vision 404 — модель устарела

Сообщение API: `gemini-2.0-flash is no longer available` → использовать **`gemini-3.6-flash`**.

В `.env` (у тебя уже почти так):

```env
VISION_PROVIDER=gemini
VISION_MODEL=gemini-3.6-flash
GEMINI_API_KEY=AIza...
```

```powershell
git pull origin agent-v2-vision
# перезапусти бота (Ctrl+C → python -m bot)
```

В коде: дефолт `gemini-3.6-flash` + fallback при 404.

Снова фото в TG. Если снова ошибка — полный текст в answers.
