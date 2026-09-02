"""Промпт: дерево фич; API только из ops_registry."""

from core.ops_registry import prompt_api_block
from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = prompt_api_block()

_LOGIC = """
## Логика сложной детали (обязательно)

Думай деревом построения, не одним эскизом:

1) БАЗА — один контур + extrude. Цилиндр: circle. Овал/крышка: stadium/rounded_rect.
2) СТУПЕНИ / БОБЫШКИ — отдельный sketch + extrude на каждую ступень.
3) ВЫРЕЗЫ — cut(depth=...) или pocket; сквозное — through_all / hole.
4) ОТВЕРСТИЯ — hole / pattern_holes_*; цековка — counterbore.
5) КАНАВКА — ring_groove / groove.
6) ФАСКИ / СКРУГЛЕНИЯ — в конце fillet/chamfer.
7) Не удаляй фичи из ТЗ. Не подставляй случайные размеры.
8) Запрещено: shell, thread, sweep, loft, sketch_on_face, win32com.
"""

_RULES = """
Сначала 3–8 строк плана по ТЗ, затем один блок ```python
с from core import Part и part.update().
Размеры только из ТЗ, буквально.
"""


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    use_mem = mem and not any(
        w in (task or "").lower()
        for w in ("build_plan", "ступен", "пробк", "вал", "feature=", "крышк", "stadium")
    )
    return (
        "Ты CAD-агент КОМПАС. Пишешь только код через core по ТЗ.\n"
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
    return (
        "Собери деталь СТРОГО по ТЗ. Все ступени, отверстия, канавки — в коде.\n"
        "Не упрощай до одной плиты. Размеры только из ТЗ.\n\n"
        f"ТЗ:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Исправь МИНИМАЛЬНО: устрани замечания, сохрани остальную геометрию.\n"
        "Только ```python.\n"
        f"Замечания:\n{err}\n\nТЗ:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
