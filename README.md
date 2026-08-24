# compas — ИИ-агент для КОМПАС-3D

Агент, который по текстовому описанию генерирует Python-код для создания 3D-моделей в **КОМПАС-3D** через высокоуровневую обёртку над COM API.

> Ветка разработки: **`dev`**  
> Ветка `main` не используется для текущей работы.

---

## Что это такое

1. Ты описываешь деталь обычным языком  
   («Втулка Ø40 наружный, Ø20 внутренний, длина 60 мм»).
2. Агент через LLM (Groq / Gemini / OpenRouter — бесплатные лимиты) генерирует Python-скрипт.
3. Скрипт использует обёртку `core` и строит модель в уже запущенном КОМПАС-3D.

Голого COM-кода в ответах агента нет — только понятный высокоуровневый API.

---

## Структура проекта

```
compas/
├── core/                 # Обёртка над COM API КОМПАС-3D
│   ├── connection.py     # Подключение / запуск КОМПАС
│   ├── part.py           # Класс Part (деталь)
│   ├── sketch.py         # Эскизы и примитивы
│   ├── operations.py     # Выдавливание, вырезание, вращение
│   └── exceptions.py
├── agent/                # ИИ-агент
│   ├── llm.py            # Клиенты Groq / Gemini / OpenRouter
│   ├── prompts.py        # Системный промпт
│   └── runner.py         # Генерация кода + CLI
├── config.py
├── requirements.txt
├── .env.example
├── WHAT_YOU_NEED_TO_DO.md  # Чеклист для тебя
└── README.md
```

---

## Требования

| Компонент | Нужно |
|-----------|--------|
| ОС | Windows |
| КОМПАС-3D | Установлен, с поддержкой API |
| Python | 3.10+ (рекомендуется 3.11) |
| LLM | Ключ одного из: Groq / Gemini / OpenRouter |

---

## Установка

```powershell
git clone https://github.com/andreytyumin05-hash/compas.git
cd compas
git checkout dev

python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# Отредактируй .env — укажи LLM_PROVIDER и соответствующий API-ключ
```

Подробный чеклист: см. **[WHAT_YOU_NEED_TO_DO.md](WHAT_YOU_NEED_TO_DO.md)**.

---

## Быстрый старт

### 1. Проверить связь с КОМПАС

Запусти КОМПАС-3D, затем:

```powershell
python -c "from core import get_app; print(get_app(auto_launch=False).visible)"
```

### 2. Сгенерировать код детали

```powershell
python -m agent.runner "Втулка: наружный диаметр 40 мм, внутренний 20 мм, длина 50 мм"
```

В консоли появится Python-код. Его можно сохранить и выполнить при запущенном КОМПАСе.

### 3. Пример ручного кода (без агента)

```python
from core import Part

part = Part.create("Втулка")

sk = part.sketch("xy")
sk.circle(0, 0, 20)          # R=20 → Ø40
part.extrude(sk, depth=50)

sk2 = part.sketch("xy")
sk2.circle(0, 0, 10)         # R=10 → Ø20
part.cut(sk2, through_all=True)
```

---

## Настройка LLM (бесплатные лимиты)

В `.env`:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
LLM_MODEL=llama-3.3-70b-versatile
LLM_TEMPERATURE=0.2
```

| Провайдер   | Где взять ключ              | Пример модели                          |
|-------------|-----------------------------|----------------------------------------|
| groq        | console.groq.com            | llama-3.3-70b-versatile                |
| gemini      | aistudio.google.com         | gemini-2.0-flash                       |
| openrouter  | openrouter.ai               | meta-llama/llama-3.3-70b-instruct:free |

Локальные модели (Ollama) намеренно не используются.

---

## API обёртки `core` (кратко)

```python
from core import Part, get_app

app = get_app()                    # подключиться или запустить КОМПАС
part = Part.create("Имя")          # новая деталь
# или
part = Part.from_active()          # уже открытая деталь

sk = part.sketch("xy")             # эскиз на плоскости xy / xz / yz
sk.circle(0, 0, 15)
sk.rectangle(-10, -5, 20, 10)
sk.line(0, 0, 30, 0)
sk.polygon([(0,0), (10,0), (10,10)], closed=True)

part.extrude(sk, depth=25)
part.cut(sk, through_all=True)
part.revolve(sk, angle=360)
part.name = "НовоеИмя"
```

---

## Текущий статус

- [x] Подключение к КОМПАС через COM (API7)
- [x] Создание детали
- [x] Эскизы: круг, прямоугольник, линия, полигон
- [x] Выдавливание и вырезание
- [x] Базовое вращение (может потребовать доработки под вашу версию)
- [x] Агент генерации кода (Groq / Gemini / OpenRouter)
- [ ] Фаски, скругления, массивы, рабочие плоскости
- [ ] Автозапуск сгенерированного скрипта
- [ ] Визуальная проверка модели (скрин + VLM)
- [ ] Примеры деталей (добавим после стабилизации core)

---

## Важно

- Работает **только на Windows** с установленным КОМПАС-3D.
- COM API чувствителен к версии КОМПАС — при ошибках присылай текст и версию программы.
- Всё развитие идёт в ветке **`dev`**. В `main` ничего не мержим без явной просьбы.

---

## Лицензия

Пока без лицензии (private repo). При необходимости добавим MIT.
