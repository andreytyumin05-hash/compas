# Что нужно сделать тебе

Ветка работы: **`dev`** (main не трогаем).

---

## 1. Окружение

- [x] venv создан
- [x] библиотеки установлены (`pip install -r requirements.txt`)
- [ ] файл **`.env`** создан (ты писал, что копию не делал — это важно)

### Обязательно создай `.env`

В корне репозитория (там же, где `README.md`):

```powershell
copy .env.example .env
```

Открой `.env` в блокноте и укажи:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=сюда_твой_ключ
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.2
```

Если ключ от Gemini:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=твой_ключ
LLM_MODEL=gemini-2.0-flash
```

Если ключ от OpenRouter:

```env
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=твой_ключ
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

**Важно:** файл должен называться именно `.env` и лежать в корне проекта (не внутри `venv`).

---

## 2. Проверка LLM (без КОМПАС)

В активированном venv, из корня репозитория:

```powershell
python -m agent.runner "Втулка: наружный диаметр 40, внутренний 20, длина 50"
```

Ожидается: в консоли появится Python-код.

Если ошибка про API key — значит `.env` не найден или ключ не тот. Пришли текст ошибки.

---

## 3. Проверка КОМПАС (COM)

1. Запусти **КОМПАС-3D** вручную.
2. Выполни:

```powershell
python -c "from core import get_app; a = get_app(auto_launch=False); print('OK visible=', a.visible)"
```

- `OK visible= True` (или False) — COM работает.
- Ошибка — пришли **полный текст** + версию КОМПАС (Справка → О программе).

---

## 4. Что пока не делать

- Не мержить `dev` → `main`
- Не запускать сгенерированный код в КОМПАСе, пока не проверим вместе первые 1–2 скрипта

---

## 5. Если что-то не так

Пришли:
1. Версию Python (`python --version`)
2. Версию КОМПАС
3. Точную команду
4. Полный текст ошибки

Я поправлю код в `dev`.
