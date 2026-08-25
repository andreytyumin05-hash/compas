# Что делать тебе сейчас

Ветка: **`agent-v2`**

## Итог диагностики (уже сделано)

- Python **64-bit** — ок  
- КОМПАС COM виден  
- **`Documents.Add(4, True)` работает** (документ создаётся)  
- Typelib **не зарегистрирована** → gencache бесполезен  
- Ломалось получение **Part** после Add и вызов `ActiveDocument3D()` как метода  

В коде это учтено: Part берём с документа, возвращённого из `Add`; `ActiveDocument3D` сначала как property.

Файл `open_ai_solve` удалён. Для локального Codex/VS Code agent: **`CODEX_TASK.md`**.

---

## Твои шаги

```powershell
cd D:\учеба\ML_study\compas
git pull origin agent-v2
```

1. Запусти **КОМПАС-3D**
2. Проверка:
   ```powershell
   python -c "from core import Part; p=Part.create('Test'); print('OK', p)"
   ```
3. Если OK — сборка:
   ```powershell
   python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
   ```
4. Если ошибка — полный текст в `responce.txt`

### Для агента в VS Code (Codex)

Открой проект, скорми агенту файл **`CODEX_TASK.md`** (или `@CODEX_TASK.md`).  
Он должен править `core/connection.py` / `core/part.py` **на этой машине** с запущенным КОМПАСом.

---

## Не нужно

- Мержить в `main`
- Менять LLM/промпты, пока COM не строит тело
