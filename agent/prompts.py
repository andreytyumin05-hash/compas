"""Системный промпт — жёсткий API + few-shot + память."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = '''
## Разрешённый API (ТОЛЬКО)

```python
from core import Part
part = Part.create("Имя")
with part.sketch("xy") as sk:   # xy | xz | yz
    sk.circle(xc, yc, radius)           # radius = D/2
    sk.rectangle(x, y, w, h)            # левый нижний угол
    sk.rounded_rect(x, y, w, h, radius=R)
    sk.stadium(x, y, length, width)     # R = width/2
    sk.ellipse(xc, yc, rx, ry)
    sk.line(x1,y1,x2,y2); sk.polygon([(x,y),...]); sk.slot(...)
part.extrude(sk, depth=H)
part.cut(sk, through_all=True)          # или depth=
part.hole(x, y, diameter=D, through_all=True)
part.pattern_holes_circular((0,0), pcd=P, count=N, diameter=D)
part.pattern_holes_rect(x1,y1,x2,y2, diameter=D)
edges = part.get_edges("all")
part.fillet(edges, radius=r); part.chamfer(edges, distance=d)
part.update()
```

ЗАПРЕЩЕНО: win32com, loft, sweep, boolean, выдуманные методы, английская проза.
Ø20 → radius=10 или hole(diameter=20). Центр детали в (0,0) по возможности.
'''

_FEW = '''
### Втулка Ø40/Ø20 L50
```python
from core import Part
part = Part.create("Втулка")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)
part.extrude(sk, depth=50)
part.hole(0, 0, diameter=20, through_all=True)
part.update()
```

### Крышка stadium 116×80 t=13 + бобышка R30 h=18
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

### Плита 100×60×8 + 4 отверстия
```python
from core import Part
part = Part.create("Плита")
with part.sketch("xy") as sk:
    sk.rectangle(0, 0, 100, 60)
part.extrude(sk, depth=8)
part.pattern_holes_rect(10, 10, 90, 50, diameter=9)
part.update()
```
'''

_RULES = '''
1. Ответ: план ≤2 строк + ОДИН блок ```python.
2. Код с колонки 0, всегда from core import Part и part.update().
3. Несколько тел: несколько sketch+extrude подряд (бобышка после базы).
4. Отверстия: hole или cut, не «второй circle в одном extrude с контуром».
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    return (
        "Ты CAD-агент КОМПАС-3D. Пишешь только код core.\n"
        + _API
        + _FEW
        + ("\n## Память успешных сборок\n" + mem + "\n" if mem else "")
        + _RULES
        + "\n## Паттерны\n"
        + load_patterns()
    )


SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    return (
        "Собери деталь. Обязателен ```python с from core import Part.\n\n"
        f"Задача:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Исправь код. Только ```python```.\n"
        f"Ошибки:\n{err}\n\nЗадача:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
