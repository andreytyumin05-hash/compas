"""Промпт: text → parametric CAD (приоритет над vision)."""

from core.ops_registry import prompt_api_block
from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = prompt_api_block() + """

## Параметры (обязательно для text-to-CAD)

```python
part.param("D1", 60)
part.param("L1", 20)
part.param("D_inner", 16)
r1 = part.p("D1") / 2
with part.sketch("xy") as sk:
    sk.circle(0, 0, r1)
part.extrude(sk, depth=part.p("L1"))
```

## Сплайн (профиль лопасти)

```python
with part.sketch("xz") as sk:
    sk.spline([(0,0), (10,5), (20,4), (30,0)], closed=False)
```
НЕ заменять spline на polyline.
"""

_LOGIC = """
## Text → parametric model

1) PARAMETERS из ТЗ (D1, L1, D_inner, ...).
2) part.param(...) для каждого.
3) Каждая цилиндрическая ступень — свой sketch + extrude.
4) Шейка = ступень меньшего Ø.
5) hole through D_inner; groove; chamfer/fillet в конце.
6) Запрещено: shell, thread, sweep, loft, sketch_on_face, win32com.
7) Не один extrude на все ступени.
"""

_RULES = """
Сначала PARAMETERS + BUILD_PLAN, затем ```python с Part, param, p, update().
"""


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    use_mem = mem and not any(
        w in (task or "").lower()
        for w in ("ступен", "штуцер", "вал", "лопаст", "канавк", "шейк")
    )
    return (
        "Ты CAD-агент КОМПАС. Цель: параметрическая редактируемая модель по тексту.\n"
        + _API
        + "\n"
        + _LOGIC
        + (("\n## Память\n" + mem + "\n") if use_mem else "")
        + _RULES
        + "\n## Справка\n"
        + load_patterns()
    )


SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    extra = ""
    try:
        from .text_contract import parse_technical_text, contract_to_codegen_hints

        c = parse_technical_text(task)
        extra = "\n\n" + contract_to_codegen_hints(c)
    except Exception:
        pass
    return (
        "Собери ПАРАМЕТРИЧЕСКУЮ деталь по ТЗ. part.param + part.p.\n\n"
        f"ТЗ:\n{task.strip()}"
        + extra
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Минимальный ремонт. Сохрани part.param и ступени.\n"
        f"Замечания:\n{err}\n\nТЗ:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
