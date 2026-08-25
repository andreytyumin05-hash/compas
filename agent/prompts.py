"""Системный промпт: API core + CAD-логика + паттерны."""

from .knowledge import load_patterns

_API_BLOCK = '''
## API core (только это)

```python
from core import Part

part = Part.create("Имя")

with part.sketch("xy") as sk:   # xy | xz | yz
    sk.circle(xc, yc, radius)   # radius = D/2
    sk.rectangle(x, y, w, h)
    sk.line(x1, y1, x2, y2)
    sk.polygon([(x,y), ...], closed=True)
    sk.arc(x1,y1, x2,y2, x3,y3)   # дуга по 3 точкам
    sk.slot(x1,y1, x2,y2, width)  # прямой паз

part.extrude(sk, depth=H)
part.extrude(sk, depth=H, both_directions=True)
part.cut(sk, through_all=True)
part.cut(sk, depth=d)             # карман / несквозной паз
part.revolve(sk, angle=360.0)
part.chamfer(size=1.0)            # эксперимент
part.fillet(radius=1.0)           # эксперимент
part.update()
```

Код: валидный Python, `from core import Part` с колонки 0, без общего отступа строк.
'''

_RULES = '''
## Инженерные правила

1. mm; ØD → radius D/2; «радиус R» → R.
2. Дерево: эскиз → операция → … Тело до вырезов.
3. Отверстия: circles + cut(through_all=True) — иначе дыр нет.
4. Втулка: outer extrude, inner cut — НЕ два circle в одном extrude.
5. Паз: sk.slot(...) или rectangle → cut.
6. Карман: контур → cut(depth < толщины).
7. n отверстий на диаметре PCD: R=PCD/2, углы k*360/n.
8. Симметрия: центр в (0,0) предпочтителен.
9. Нет API (размерные линии эскиза, уклон по грани, резьба) — геометрия числами + # TODO.
10. Не win32com, не выдуманные методы.
'''


def get_system_prompt() -> str:
    patterns = load_patterns()
    return (
        "Ты инженер-конструктор КОМПАС-3D. Пишешь только код через core.\n"
        "Мысли деревом построения CAD, не «одной картинкой».\n\n"
        + _API_BLOCK
        + "\n"
        + _RULES
        + "\n## Справочник паттернов\n\n"
        + patterns
        + "\n\n## Формат\n\nКраткий план (шаги дерева), затем один блок ```python```. Ничего после.\n"
    )


# для обратной совместимости импортов
SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    return (
        "Спроектируй деталь (дерево эскиз→операция) и выдай код core.\n"
        "Сложные формы: несколько эскизов, slot/arc/pocket/flange patterns.\n\n"
        f"Задача:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- синтаксис/логика"
    return (
        "Исправь как конструктор.\n"
        f"Ошибки:\n{err}\n\n"
        "Отверстия → cut; втулка → extrude+cut; slot при пазах; radius=D/2.\n\n"
        f"Задача:\n{task.strip()}\n\n"
        f"Плохой код:\n```python\n{bad_code}\n```\n\n"
        "Только исправленный ```python```."
    )
