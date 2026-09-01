# Visual Fluent v2

Цель: агент не только строит тело, но и:
1. объявляет **переменные** размеров (`part.var("D", 40)`)
2. заполняет **свойства** (`set_properties`)
3. ставит вид и делает **screenshot** для visual loop

## API

```python
part.var("D", 40, comment="наружный Ø")
part.set_properties(designation="...", name="Втулка", material="Сталь 20")
part.set_view("iso")  # iso|front|top|...
path = part.screenshot("session/preview.png")  # Path | None
ctx = part.get_context()  # dict сессии
```

COM best-effort: если API v23 не принял переменную/снимок — возвращается False/None, **build не падает**. Значения дублируются в `get_context()`.

## Проверки

- `validate_generated_code` — жёсткие ошибки (синтаксис, imports)
- `critic_warnings` — мягкие (нет var / properties / visual)
- runner печатает warnings и может отдать их в repair-prompt

## Offline

```powershell
python -m unittest tests.test_visual_and_vars -v
```
