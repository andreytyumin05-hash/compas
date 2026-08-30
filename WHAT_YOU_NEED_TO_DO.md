# Сейчас

```powershell
git pull origin agent-v2-vision
python -m core.smoke_edges
```

## Фикс по последнему answers

`GetDefinition invoke: Член группы не найден` — снова вызывали **`()``** у property.  
Как с `ActiveDocument3D`: писать `entity.GetDefinition` **без скобок**. То же для `First`/`Next` на коллекции рёбер.

Ждём `OK` в smoke_edges. Лог → `answers.txt`.

## Бот (уже в ветке)

| Возможность | Статус |
|-------------|--------|
| Текст → build | да |
| **Фото чертежа** | да (`filters.PHOTO` → vision → кнопки верно/нет) |
| Очередь (1 КОМПАС) | да |
| Прислать **STEP** | да, если `Part.export` сработает |
| **Удалить tmp** | да (`session_workspace` + `safe_delete_path` в `finally`) |
| Закрыть документ в КОМПАС | пока нет (модель остаётся открытой) |
| Нативный `.m3d` | ещё нет |

`.env`:
```
TELEGRAM_BOT_TOKEN=
GROQ_API_KEY=
GEMINI_API_KEY=          # без него фото не распознает
```

```powershell
python -m bot
```
