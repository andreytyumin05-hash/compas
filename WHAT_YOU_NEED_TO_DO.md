# «пустой код» — что это

Vision **ок** (крышка/flange распознана). Упало на **генерации Python** через Groq: модель вернула текст без блока ` ```python ` (или совсем пусто) → validate: «пустой код».

## Исправлено в ветке
- повторный запрос «только python-блок»
- извлечение кода из сырого текста / think-тегов
- чтение content у reasoning-моделей Groq
- few-shot для stadium ≈ rounded_rect

```powershell
git pull origin agent-v2-vision
# перезапуск бота
python -m bot
```

Локально без бота:
```powershell
python -m agent.runner "Крышка 116x80 толщина 13, rounded, бобышка R30 высота 18"
```

Если снова пусто — `python -m agent.list_models` и поставь в `.env` явную chat-модель, например:
```env
LLM_MODEL=llama-3.3-70b-versatile
```
