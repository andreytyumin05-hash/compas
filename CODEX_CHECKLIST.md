# Задание для локального агента VS Code (Codex / Copilot)

Репозиторий: `compas`, ветка **`agent-v2-vision`** (не `main`).  
ОС: Windows, КОМПАС-3D **v23** должен быть **запущен**. Python venv проекта активен.

Твоя цель: **проверить и починить** построение stadium/крышки через `core.sketch.rounded_rect`, затем убедиться что `agent.build` и бот доходят до успешного `extrude`.

---

## Контекст (что уже известно)

1. Vision (Gemini) и шаблоны (`agent/templates.py`) работают — размеры крышки распознаются.
2. LLM-каскад настроен (`agent/llm.py`): Gemini → Groq light → strong.
3. **Падает КОМПАС COM**, не сеть:
   ```
   rounded_rect: (-2147352561, 'Параметр является обязательным.', None, None)
   ```
4. Причина: вызов дуги эскиза без обязательного параметра SDK. В API5 2D:
   - `ksArcByPoint(x1,y1, x2,y2, x3,y3, **direction**, style)` — **direction** = 1 или -1
   - `ksArcByAngle(xc, yc, radius, ang1, ang2, **direction**, style)` — углы в градусах
5. В `core/sketch.py` уже пытались добавить direction / ArcByAngle — **нужно проверить на живом КОМПАС**, добить сигнатуру под v23 typelib/late-binding.

---

## Что проверить по шагам

### 1. Smoke дуг (главное)

```powershell
cd D:\учеба\ML_study\compas
.\venv\Scripts\Activate.ps1
git pull origin agent-v2-vision
python -m core.smoke_rounded
```

- Ожидание: `OK: stadium 116x80 R40 + boss R30 h18` и деталь в КОМПАС с **гладкими** торцами (не ломаная).
- Если FAIL — читай traceback, правь **только** `core/sketch.py` методы:
  - `_ks_arc_angle`
  - `_ks_arc_3pt`
  - `rounded_rect`

### 2. Диагностика реального API 2D (если smoke падает)

Напиши короткий скрипт (можно временно `core/probe_arc.py`) который:

1. `Part.create` + `with part.sketch("xy") as sk`
2. Через `sk._ensure()` / `BeginEdit` получает `doc2d`
3. Печатает callable-имена: всё что содержит `Arc` / `arc` / `Circle` / `Line`
4. Пробует варианты вызовов и пишет какой **не** кидает «Параметр является обязательным»:

```text
ksArcByPoint(x1,y1,x2,y2,x3,y3, direction, style)
ksArcByAngle(xc,yc,r, ang1, ang2, direction, style)
ksArcByAngle(... другие порядки аргументов ...)
```

Зафиксируй рабочую сигнатуру в `rounded_rect` и удали probe после фикса.

### 3. Полная крышка без бота

```powershell
python -m agent.build "Крышка length=116 width=80 thickness=13 outer_radius=40 boss_height=18 inner_radius=30"
```

Должен сработать **шаблон** (`agent/templates.py`) без LLM.  
Успех: `Готово.` + тело в КОМПАС.

### 4. Регрессии (не сломать)

```powershell
python -m core.smoke_active
python -m core.smoke_edges
python -m core.smoke_export
```

`smoke_edges` ранее был 4/4 — не ухудшить fillet/chamfer.

### 5. Бот (после фикса core)

```powershell
python -m bot
```

В TG: фото крышки → «Верно, строить» → файлы `.m3d`/`.step` или хотя бы модель в КОМПАС.

---

## Файлы, которые можно менять

| Файл | Зачем |
|------|--------|
| `core/sketch.py` | **основной фикс** дуг / rounded_rect / stadium |
| `core/smoke_rounded.py` | тест |
| `agent/templates.py` | только если шаблон даёт неверные числа |
| `docs/` или комментарии | сигнатура API для будущего |

**Не трогать:** `main`, секреты `.env`, не коммитить токены.

---

## Ограничения КОМПАС v23 (late-binding)

- `GetDefinition`, `BeginEdit`, `Create`, `First`, `Next` — часто **property**, не вызывать как `()`.
- `o3d_edge = 7` (не 8 — это vertex).
- Ошибки COM:
  - `-2147352573` член группы не найден → лишний `()`
  - `-2147352561` параметр обязательный → не хватает аргумента (наш случай с arc)

---

## Критерий «готово»

1. `python -m core.smoke_rounded` → OK  
2. `python -m agent.build "Крышка length=116 ..."` → Готово  
3. В модели скругления **дуги**, не многоугольник из отрезков  
4. Краткий отчёт: какая сигнатура `ksArc*` сработала на v23  

Работай только в ветке `agent-v2-vision`. Коммить осмысленно.
