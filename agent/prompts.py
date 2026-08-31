"""Промпт: полное дерево фич, цилиндрические ступени."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = '''
## API (только это)

```python
from core import Part
part = Part.create("Имя")
with part.sketch("xy") as sk:  # xy|xz|yz
    sk.circle(xc, yc, radius)          # radius = Ø/2
    sk.rectangle(x, y, w, h)
    sk.rounded_rect(x, y, w, h, radius=R)
    sk.stadium(x, y, length, width)
    sk.polygon([(x,y),...])            # шестигранник и т.п.
part.extrude(sk, depth=H)              # база или следующая ступень
part.cut(sk, depth=D)                  # глухой вырез
part.cut(sk, through_all=True)         # сквозной
part.hole(x, y, diameter=D, through_all=True)
part.hole(x, y, diameter=D, depth=H, through_all=False)
part.pattern_holes_circular((0,0), pcd=P, count=N, diameter=D)
edges = part.get_edges("all")
part.fillet(edges, radius=r)
part.chamfer(edges, distance=d)
part.update()
```

Запрещено: win32com, loft, sweep, part.step(), part.slot() как методы Part — только sketch+extrude/cut.
'''

_LOGIC = '''
## Обязательная логика

1. Читай ТЗ целиком. Каждая ступень с своим Ø и длиной = отдельный circle + extrude.
2. Пробка/вал/штуцер: НЕ rectangle. Только соосные цилиндры (несколько extrude).
3. Канавка: cut кольцевым контуром или меньший/больший цилиндр по смыслу ТЗ.
4. Шестигранное углубление: polygon(6) + cut(depth=...).
5. Карман/глухой вырез: cut(depth=...), НЕ extrude «добавки вместо выреза».
6. Порядок: все наружные ступени (extrude) → вырезы/отверстия (cut/hole) → chamfer/fillet.
7. Не упрощай многоступенчатую деталь до одной плиты или одного цилиндра.
'''

_RULES = '''
Ответ: краткий план (База→Ступени→Вырезы→Кромки) + один ```python
from core import Part ... part.update()
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    return (
        "Ты CAD-агент КОМПАС. Код только через core.\n"
        + _API
        + _LOGIC
        + (("\n## Память\n" + mem + "\n") if mem else "")
        + _RULES
        + "\n## Справка\n"
        + load_patterns()
    )


SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    return (
        "Построй ВСЮ деталь по ТЗ. Ступени = отдельные extrude, "
        "вырезы = cut/hole. Не заменяй на параллелепипед.\n\n"
        f"ТЗ:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Исправь. Только ```python. Сохрани все ступени и вырезы из ТЗ.\n"
        f"Ошибки:\n{err}\n\nТЗ:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
