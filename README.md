# compas — текст → 3D-модель в КОМПАС-3D

Проект связывает языковую модель (LLM) с российской CAD-системой **КОМПАС-3D**: вы описываете деталь обычным текстом (втулка, фланец, плита с отверстиями), агент генерирует Python-код только через узкую обёртку `core`, этот код исполняется на Windows и через **COM Automation** строит эскизы и операции в уже запущенном КОМПАСе. Для диалога с моделью используются облачные API с бесплатными лимитами — **Groq**, **Google Gemini** или **OpenRouter** (ключ в `.env`); для геометрии — штатный COM КОМПАС (`Kompas.Application.5` / `.7`, `Documents.Add`, `NewEntity`, `ksCircle` и т.д.), без ручного кликанья по каждому контуру. Опционально тот же конвейер доступен из **Telegram-бота** на том же ПК: сообщение → LLM → `core` → КОМПАС. Рабочая ветка разработки — **`agent-v2`**; команды вроде `python -m agent.build "…"` — основной способ проверки.

---

## Как устроен поток данных

```text
Текст задачи
    │
    ▼
agent (LLM: Groq / Gemini / OpenRouter)
    │  system prompt + knowledge/CAD_PATTERNS.md
    │  → Python-код только с `from core import Part`
    ▼
validate + code_fix (+ retry при дырках без cut)
    │
    ▼
exec → core.Part / Sketch / operations
    │
    ▼
win32com → КОМПАС-3D (эскиз, выдавливание, вырез)
```

1. **LLM** не вызывает COM напрямую и не пишет `win32com` — только публичный API `core`.
2. **`core`** переводит высокоуровневые вызовы (`sketch`, `extrude`, `cut`) в COM API5/API7.
3. **КОМПАС** должен быть установлен и, как правило, **уже запущен** (подключение через `GetActiveObject`).

---

## Требования

| Компонент | Зачем |
|-----------|--------|
| Windows x64 | COM КОМПАС работает на Windows |
| КОМПАС-3D | целевая CAD |
| Python 3.10+ (лучше 3.12 x64; 3.14 тоже встречался) | runtime |
| `pywin32` | COM |
| ключ LLM | генерация кода |

---

## Быстрый старт

```powershell
git checkout agent-v2
git pull origin agent-v2

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# заполнить GROQ_API_KEY (или GEMINI / OPENROUTER) и при необходимости LLM_MODEL
```

Запустить **КОМПАС-3D**, затем:

```powershell
python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
python -m agent.build "Фланец диаметр 80 толщина 10, центр отверстие 20, 4 отверстия 9 на диаметре 55"
```

Только сгенерировать код без запуска в CAD:

```powershell
python -m agent.runner "Плита 100x60x8, 4 отверстия диаметр 9 по углам отступ 10"
```

---

## Переменные окружения (`.env`)

Шаблон — `.env.example` (сам `.env` в git не коммитится).

| Переменная | Назначение |
|------------|------------|
| `LLM_PROVIDER` | `groq` (по умолчанию), `gemini`, `openrouter` |
| `GROQ_API_KEY` | ключ [console.groq.com](https://console.groq.com) |
| `GEMINI_API_KEY` | ключ Google AI Studio |
| `OPENROUTER_API_KEY` | ключ OpenRouter |
| `LLM_MODEL` | id модели (например `llama-3.3-70b-versatile` или актуальная с Groq) |
| `TELEGRAM_BOT_TOKEN` | токен от @BotFather для `python -m bot` |
| `COMPAS_DEBUG_COM` | `1` — подробный лог COM в operations |

Список моделей Groq на ключе:

```powershell
python -m agent.list_models
```

---

## Команды

| Команда | Что делает |
|---------|------------|
| `python -m agent.build "…"` | LLM → проверка → **исполнение в КОМПАС** |
| `python -m agent.runner "…"` | LLM → код в терминал (без CAD) |
| `python -m agent.list_models` | модели Groq для ключа |
| `python -m core.diagnose` | диагностика COM (App5/App7, Documents, Part) |
| `python -m core.smoke_active` | цилиндр в **уже открытой** детали |
| `python -m bot` | Telegram long-polling → тот же `run_task` |

Примеры задач:

```text
Втулка наружный 40 внутренний 20 длина 50
Плита 100x60x8, 4 отверстия диаметр 9 по углам отступ 10
Фланец диаметр 80 толщина 10, центр отверстие 20, 4 отверстия 9 на диаметре 55
```

---

## Структура репозитория

```text
compas/
├── agent/           # LLM-агент: промпт, генерация, валидация, build
├── core/            # обёртка над COM КОМПАС
├── bot/             # Telegram-бот (опционально)
├── knowledge/       # CAD-паттерны для промпта
├── requirements.txt
├── .env.example
├── README.md
└── WHAT_YOU_NEED_TO_DO.md   # краткий чеклист «что делать сейчас»
```

Ниже — только **нужные** файлы и их роли.

---

### `core/` — связь с КОМПАС-3D

Слой, который реально двигает CAD. LLM сюда не ходит напрямую; сгенерированный скрипт импортирует `Part`.

| Файл | Роль |
|------|------|
| **`connection.py`** | Подключение COM: `GetActiveObject("Kompas.Application.5")` и `.7`, создание документа (`Documents.Add(4, True)` и запасные пути), извлечение **API5 `ksPart`** (с `NewEntity`) из документа. Константы типов сущностей (эскиз, выдавливание, вырез). |
| **`part.py`** | Класс **`Part`**: `create`, `from_active`, `sketch`, `extrude`, `cut`, `revolve`, `chamfer`, `fillet`, `update`. Точка входа для скриптов агента. |
| **`sketch.py`** | Эскиз: `BeginEdit` / `EndEdit`, `circle`, `line`, `rectangle`, `polygon`, `arc`, `slot`. Рисует 2D-контур через `ksCircle` / `ksLineSeg` и др. |
| **`operations.py`** | 3D-операции: `extrude`, `cut_extrude`, `revolve` — `NewEntity`, параметры выдавливания, `SetSketch`, `Create`. |
| **`part_advanced.py`** | Экспериментальные **фаска / скругление** (`chamfer` / `fillet`); id операций зависят от версии КОМПАС. |
| **`exceptions.py`** | `KompasError`, `KompasNotRunningError`, `KompasOperationError`. |
| **`diagnose.py`** | Диагностика: окружение, App5/App7, `Documents.Add`, `from_active`. Запуск: `python -m core.diagnose`. |
| **`smoke_active.py`** | Дымовой тест геометрии на активной детали. |
| **`__init__.py`** | Реэкспорт `Part` и ошибок для `from core import Part`. |

**Взаимодействие:** `Part.create` → `KompasApp.new_part_document` → `Part.sketch` → `Sketch` → `operations.extrude` / `cut`.

---

### `agent/` — языковая модель и конвейер кода

| Файл | Роль |
|------|------|
| **`llm.py`** | Клиенты **Groq / Gemini / OpenRouter**, чтение `.env`, `get_llm_client()`, выбор модели Groq. |
| **`prompts.py`** | System prompt: разрешённый API `core`, правила CAD, формат ответа; `build_user_prompt` / `build_repair_prompt`. Подмешивает patterns через `knowledge.py`. |
| **`knowledge.py`** | Читает `knowledge/CAD_PATTERNS.md` (с лимитом длины) и отдаёт текст в промпт. |
| **`runner.py`** | Класс **`Agent`**: chat → извлечение ```python``` → нормализация → `generate_checked` с retry. CLI без исполнения в CAD. |
| **`code_fix.py`** | Выравнивание отступов LLM, эвристики «отверстия без cut». |
| **`validate.py`** | Статика: `from core import Part`, `Part.create`, запрет `win32com` и лишних import. |
| **`build.py`** | Полный цикл: generate → validate → **`exec`** кода (импорт `core` → КОМПАС). Функция `run_task` для CLI и бота. |
| **`list_models.py`** | Печать моделей Groq для текущего ключа. |
| **`__main__.py`** | `python -m agent` → runner. |
| **`__init__.py`** | Пакет agent. |

**Взаимодействие:** `build` / `runner` → `Agent` → `llm` + `prompts` (+ patterns) → `validate` / `code_fix` → (в build) `exec` → `core`.

---

### `bot/` — Telegram

| Файл | Роль |
|------|------|
| **`__main__.py`** | Long-polling (`python-telegram-bot`): `/start`, текст → `agent.build.run_task` в thread → ответ с кодом или ошибкой. **КОМПАС и Python на том же компьютере**, что и бот. |
| **`__init__.py`** | Пакет. |

```powershell
# .env: TELEGRAM_BOT_TOKEN=...
# КОМПАС открыт
python -m bot
```

---

### `knowledge/` — подсказки CAD для модели

| Файл | Роль |
|------|------|
| **`CAD_PATTERNS.md`** | Короткие схемы: плита, втулка, фланец, паз, карман, правила размеров. Не архив полных скриптов. Подмешивается в system prompt. |

---

### Корень репозитория

| Файл | Роль |
|------|------|
| **`requirements.txt`** | `pywin32`, `python-dotenv`, `groq`, `google-generativeai`, `openai`, `rich`, `httpx`, `python-telegram-bot`. |
| **`.env.example`** | Шаблон секретов и провайдера LLM. |
| **`.gitignore`** | venv, `.env`, логи, ответы отладки, файлы моделей КОМПАС. |
| **`WHAT_YOU_NEED_TO_DO.md`** | Актуальный чеклист для разработки/проверок. |
| **`README.md`** | Этот документ. |

Файлы вроде локальных логов проверок **не** являются частью архитектуры; в git их лучше не держать.

---

## API, которые реально используются

### LLM (HTTPS)

- **Groq** — Chat Completions (`groq` SDK).
- **Gemini** — `google.generativeai`.
- **OpenRouter** — OpenAI-совместимый endpoint.

### КОМПАС (локальный COM, `pywin32`)

- ProgID: `Kompas.Application.5`, `Kompas.Application.7`.
- Создание детали: чаще `Documents.Add(4, True)` (API7), part через API5-совместимый путь (`GetPart` / `ActiveDocument3D` как property).
- Моделирование: `NewEntity` (эскиз, base/boss/cut extrusion, revolve), `BeginEdit` / `ksCircle` / `ksLineSeg`, `SetSketch`, `Create`.

Typelib (`gencache`) на многих установках **не зарегистрирована** — код рассчитан на late binding без обязательного makepy.

### Telegram

- Bot API через `python-telegram-bot` (polling). Токен только в `.env`.

---

## Публичный API `core` (что может генерировать агент)

```python
from core import Part

part = Part.create("Имя")

with part.sketch("xy") as sk:   # xy | xz | yz
    sk.circle(xc, yc, radius)   # радиус = диаметр/2
    sk.rectangle(x, y, w, h)
    sk.line(x1, y1, x2, y2)
    sk.polygon([(x, y), ...], closed=True)
    sk.arc(x1, y1, x2, y2, x3, y3)
    sk.slot(x1, y1, x2, y2, width)

part.extrude(sk, depth=10.0)
part.cut(sk, through_all=True)
part.cut(sk, depth=3.0)
part.revolve(sk, angle=360.0)
part.chamfer(size=1.0)   # эксперимент
part.fillet(radius=1.0)  # эксперимент
part.update()
```

---

## Типичные ограничения

- Только **Windows + установленный КОМПАС**.
- Нет полноценных параметрических размерных линий эскиза «как в UI» — геометрия задаётся числами.
- Фаска/скругление — экспериментально; уклон, резьба, массив — пока не в стабильном API.
- Плоскости эскиза в обёртке: в основном **xy / xz / yz**.
- Бот не «облачный CAD»: COM только на машине, где крутится Python и КОМПАС.

---

## Ветки

| Ветка | Назначение |
|-------|------------|
| **`agent-v2`** | Актуальная разработка — с неё и работать |
| `main` | Более ранний baseline; подтягивать merge с agent-v2 по готовности |

---

## Отладка COM

```powershell
python -m core.diagnose
```

Если документ создаётся, а part нет — смотреть вывод diagnose. Геометрия на уже открытой детали:

```powershell
# в КОМПАС: Файл → Создать → Деталь
python -m core.smoke_active
```

Подробный лог операций: `COMPAS_DEBUG_COM=1`.

---

## Лицензия и назначение

Учебно-исследовательский конвейер «自然语言 / текст → КОМПАС». Не заменяет нормы ЕСКД и ручную проверку модели конструктором.
