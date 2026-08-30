"""Системный промпт: API core + CAD + few-shot."""

from .knowledge import load_patterns

_API_BLOCK = '''
## API core (только это)

```python
from core import Part

part = Part.create("Имя")

with part.sketch("xy") as sk:
    sk.circle(xc, yc, radius)
    sk.rectangle(x, y, w, h)
    sk.rounded_rect(x, y, w, h, radius=5)
    sk.ellipse(xc, yc, rx, ry)
    sk.line(x1, y1, x2, y2)
    sk.polygon([(x,y), ...], closed=True)
    sk.arc(x1,y1, x2,y2, x3,y3)
    sk.slot(x1,y1, x2,y2, width)
    sk.spline([(x,y), ...], closed=False)

part.extrude(sk, depth=H)
part.cut(sk, through_all=True)
part.cut(sk, depth=d)
part.revolve(sk, angle=360.0)
part.hole(x, y, diameter=D, through_all=True)
part.pattern_holes_circular((0,0), pcd=55, count=4, diameter=9)
part.pattern_holes_rect(10, 10, 90, 50, diameter=9)
edges = part.get_edges("all")
part.fillet(edges, radius=1.0)
part.chamfer(edges, distance=0.5)
part.update()
```

Нет loft/sweep/boolean. «Stadium»/овал ≈ rounded_rect или slot.
'''

_FEW_SHOT = '''
## Примеры

### Втулка
```python
from core import Part
part = Part.create("Втулка")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)
part.extrude(sk, depth=50)
part.hole(0, 0, diameter=20, through_all=True)
part.update()
```

### Крышка/плита stadium ≈ rounded_rect
```python
from core import Part
part = Part.create("Крышка")
with part.sketch("xy") as sk:
    sk.rounded_rect(-58, -40, 116, 80, radius=40)
part.extrude(sk, depth=13)
with part.sketch("xy") as sk2:
    sk2.circle(0, 0, 30)
part.extrude(sk2, depth=18)
part.update()
```
'''

_RULES = '''
## Правила
1. mm; hole(diameter=...); circle radius=D/2.
2. Ответ ОБЯЗАН содержать блок ```python с from core import Part.
3. Не отвечай пустым текстом и не только планом без кода.
4. Код с колонки 0.
'''


def get_system_prompt() -> str:
    patterns = load_patterns()
    return (
        "Ты инженер-конструктор КОМПАС-3D. Только core.\n"
        + _API_BLOCK
        + _FEW_SHOT
        + _RULES
        + "\n## Паттерны\n\n"
        + patterns
        + "\n\nФормат: кратко план, затем ОБЯЗАТЕЛЬНО ```python```.\n"
    )


SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    return (
        "Спроектируй деталь. В конце ответа обязателен блок ```python.\n\n"
        f"Задача:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Исправь. Ответ — только ```python```.\n"
        f"Ошибки:\n{err}\n\n"
        f"Задача:\n{task.strip()}\n\n"
        f"Плохой код:\n```python\n{bad_code}\n```\n"
    )
