# Фикс бота (импорт core)

Ошибка была:
```
TypeError: __bases__ assignment: 'FluentMixin' deallocator differs from 'object'
```
в `core/__init__.py` при `python -m bot`.

```powershell
git pull origin feature/visual-fluent-v2

# проверка импорта без КОМПАС
python -c "from bot.sessions import session_workspace; print('ok')"

python -m bot
```

В Telegram: фото чертежа → vision → кнопки Строить / Неверно.
Нужны `TELEGRAM_BOT_TOKEN` и `GEMINI_API_KEY` в `.env`, КОМПАС на ПК.
