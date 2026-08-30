# Сейчас

## Фаски — готово
`python -m core.smoke_edges` → **Passed 4/4** (по твоему answers).

## Новое после этого коммита

1. **Экспорт `.m3d`** (нативный) + `.step`
2. **`part.close()`** — закрытие документа после отдачи файлов
3. Бот шлёт **оба** файла и чистит tmp

```powershell
git pull origin agent-v2-vision

# опционально проверить SaveAs
python -m core.smoke_export
```

## Бот

`.env`:
```
TELEGRAM_BOT_TOKEN=
GROQ_API_KEY=
GEMINI_API_KEY=
```

```powershell
# КОМПАС открыт
python -m bot
```

Проверки в TG:
1. `/start`
2. Текст: `Втулка наружный 40 внутренний 20 длина 50`
3. Фото чертежа (нужен Gemini) → кнопки → сборка
4. Должны прийти `part.m3d` и/или `part.step`, локальный `.compas_tmp` пустеет

Если файл не пришёл — модель всё равно может быть в КОМПАС; пришли текст ошибки из чата.
