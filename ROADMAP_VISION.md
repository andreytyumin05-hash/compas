# План agent-v2-vision (main не трогаем)

## Новая / изменённая структура

```text
core/
  sketch.py          # + ellipse, rounded_rect, spline
  features.py        # hole, pattern_linear/circular (эскиз-уровень)
  export.py          # STEP/STL, temp dirs, safe delete
  mass.py            # масса/объём best-effort
  part.py            # тонкие обёртки новых методов
  part_advanced.py   # chamfer/fillet (эксперимент)

agent/
  vision.py          # чертёж → JSON-спецификация
  schema.py          # JSON schema фич
  prompts.py         # few-shot + сложный API
  validate.py        # размеры/осмысленность
  build.py           # retry при ошибке COM
  runner.py

bot/
  __main__.py        # текст + фото, confirm, очередь
  queue.py           # serial queue для одного КОМПАС
  sessions.py        # tmp на user_id+uuid, cleanup

knowledge/CAD_PATTERNS.md
```

## Этапы

1. **core** — примитивы + export + hole/pattern helpers  
2. **agent** — промпт, validate, COM-retry  
3. **vision** — Gemini/OpenRouter image → JSON  
4. **bot** — очередь, confirm, файл, delete  

## Честно про КОМПАС COM

Полный loft/sweep/boolean/сборка/выбор рёбер фаски — тяжёлый API, зависит от версии.  
В коде: рабочие пути там, где API5 стабилен; иначе `KompasOperationError` с понятным текстом, без падения на сырой COM.
