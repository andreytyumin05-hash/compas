# Что нужно сделать тебе

Этот файл — чеклист. Пока код на ветке `dev` и не трогает `main`.

---

## 1. Окружение Windows

- [ ] Установлен **КОМПАС-3D** (версия с поддержкой API / SDK).
- [ ] При установке была включена опция API / SDK (если предлагалась).
- [ ] Установлен **Python 3.10+** (лучше 3.11).
- [ ] Python добавлен в PATH.

Проверка: открой PowerShell и выполни `python --version`.

---

## 2. Клонирование и зависимости

```powershell
git clone https://github.com/andreytyumin05-hash/compas.git
cd compas
git checkout dev

python -m venv venv
.\venv\Scripts\activate

pip install -r requirements.txt
```

---

## 3. Ключи LLM (бесплатные лимиты)

Выбери **один** провайдер:

### Вариант A — Groq (рекомендуется для старта)
1. Зайди на https://console.groq.com
2. Создай API-ключ
3. В `.env`:
   ```
   LLM_PROVIDER=groq
   GROQ_API_KEY=твой_ключ
   LLM_MODEL=llama-3.3-70b-versatile
   ```

### Вариант B — Google Gemini
1. https://aistudio.google.com → Get API key
2. В `.env`:
   ```
   LLM_PROVIDER=gemini
   GEMINI_API_KEY=твой_ключ
   LLM_MODEL=gemini-2.0-flash
   ```

### Вариант C — OpenRouter (бесплатные модели)
1. https://openrouter.ai
2. В `.env`:
   ```
   LLM_PROVIDER=openrouter
   OPENROUTER_API_KEY=твой_ключ
   LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
   ```

Скопируй шаблон:
```powershell
copy .env.example .env
# отредактируй .env
```

---

## 4. Первая проверка подключения к КОМПАС

1. Запусти КОМПАС-3D вручную.
2. В активированном venv:

```powershell
python -c "from core import get_app; app = get_app(auto_launch=False); print('OK', app.visible)"
```

Если видишь `OK True` (или `OK False`) — COM работает.

Если ошибка — пришли полный текст, разберём.

---

## 5. Проверка генерации кода агентом

```powershell
python -m agent.runner "Простая втулка: внешний диаметр 40 мм, внутренний 20 мм, длина 50 мм"
```

Должен появиться Python-код. **Пока не запускай его в КОМПАСе** — сначала посмотрим вместе, что генерируется.

---

## 6. Что пока не нужно делать

- Не мержи `dev` в `main`
- Не жди идеальной работы всех операций сразу (revolve и сложные оси будут дорабатываться)
- Не ставь локальные модели (Ollama) — договорились использовать облачные лимиты

---

## 7. Как мы будем двигаться дальше

1. Ты проверяешь `get_app` и присылаешь результат.
2. Пробуем сгенерировать 1–2 простых скрипта и запускаем их у тебя.
3. По ошибкам COM дорабатываем `core/` (это нормально — API капризный).
4. Потом расширяем операции (фаски, массивы, плоскости и т.д.) и улучшаем агента.

---

## Если что-то сломалось

Пришли:
- версию КОМПАС-3D
- версию Python
- полный текст ошибки
- что именно делал (команда)

Я поправлю код в ветке `dev`.
