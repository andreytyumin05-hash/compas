"""Системный промпт."""

from .knowledge import load_patterns

_API = '''
## API (только это)

```python
from core import Part
part = Part.create("Имя")
with part.sketch("xy") as sk:  # xy|xz|yz
    sk.circle(xc, yc, radius)
    sk.rectangle(x, y, w, h)
    sk.rounded_rect(x, y, w, h, radius=R)  # дуги, не ломаная
    sk.stadium(x, y, length, width)        # овал R=width/2
    sk.ellipse(xc, yc, rx, ry)
    sk.line / sk.polygon / sk.arc / sk.slot / sk.spline
part.extrude(sk, depth=H)
part.cut(sk, through_all=True)  # или depth=
part.hole(x, y, diameter=D, through_all=True)
part.pattern_holes_circular((0,0), pcd=55, count=4, diameter=9)
part.pattern_holes_rect(10, 10, 90, 50, diameter=9)
edges = part.get_edges("all")
part.fillet(edges, radius=1.0)
part.chamfer(edges, distance=0.5)
part.update()
```
Stadium/oblong → rounded_rect или stadium, НЕ polygon из точек.
'''

_FEW = '''
### Крышка stadium + бобышка
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
'''

_RULES = '''
1. mm; hole(diameter=...); circle — радиус.
2. Ответ: один блок ```python с from core import Part. Без английской прозы.
3. Код с колонки 0.
'''


def get_system_prompt() -> str:
    return (
        "Инженер КОМПАС, только core.\n"
        + _API
        + _FEW
        + _RULES
        + "\n## Паттерны\n"
        + load_patterns()
        + "\nФормат: план (1–3 строки) + ```python```.\n"
    )


SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    return f"Спроектируй деталь. Обязателен блок ```python.\n\nЗадача:\n{task.strip()}"


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Только исправленный ```python```, без текста вокруг.\n"
        f"Ошибки:\n{err}\n\nЗадача:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2000]}\n```\n"
    )
