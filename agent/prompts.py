"""Кодоген: BUILD_PLAN + core API, опциональные размеры эскиза."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = '''
## API core

```python
from core import Part
part = Part.create("Имя")
with part.sketch("xy") as sk:  # xy|xz|yz
    sk.circle(xc, yc, radius)           # radius = Ø/2
    sk.rectangle(x, y, w, h)
    sk.rounded_rect(...); sk.stadium(...)
    sk.polygon([(x,y),...])
    # размеры (желательно; если API вернёт False — не страшно)
    sk.dim_radial(xc, yc, radius)
    sk.dim_linear(x1, y1, x2, y2)
part.extrude(sk, depth=H)
part.cut(sk, depth=D)                  # глухой
part.cut(sk, through_all=True)
part.hole(x, y, diameter=D, through_all=True)
part.hole(x, y, diameter=D, depth=H, through_all=False)
part.pattern_holes_circular((0,0), pcd=P, count=N, diameter=D)
part.pattern_holes_linear(start, count, step, diameter=D)
part.pattern_holes_points([(x,y),...], diameter=D)
part.boss(x, y, diameter=D, height=H)
part.hex_boss(x, y, diameter=D, height=H)
part.pocket(x, y, diameter=D, depth=H)
part.ring_groove(x, y, outer_diameter=..., inner_diameter=..., depth=...)
part.counterbore(x, y, pilot_diameter=..., counterbore_diameter=..., counterbore_depth=..., through_all=True)
part.countersink(x, y, pilot_diameter=..., countersink_diameter=..., depth=...)
part.keyway(x, y, length=..., width=..., depth=...)
part.slot(x1,y1,x2,y2, width=..., through_all=True)
edges = part.get_edges("all")
part.fillet(edges, radius=r)
part.chamfer(edges, distance=d)
part.update()
```
'''

_LOGIC = '''
## Как рассуждать

1. BUILD_PLAN — по шагам, ничего не выкидывать.
2. Пунктир/оси — не наружный контур.
3. Одинаковые отверстия по кругу → pattern_holes_circular.
4. Ступени вала/пробки: circle + extrude на каждую; не один rectangle.
5. Карман/шестигранник: polygon/pocket + cut(depth=...).
6. Цековка → counterbore; канавка → ring_groove; фаски/скругления в конце + get_edges.
7. После основных контуров можно dim_radial/dim_linear (не обязательно для успеха).
8. Не подгонять под «типовую плиту».
'''

_RULES = '''
Сначала 3–6 строк плана, затем один блок ```python
с from core import Part и part.update(). Без win32com/loft/sweep.
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    use_mem = mem and not any(
        w in (task or "").lower()
        for w in ("build_plan", "ступен", "пробк", "вал", "feature=", "body_style")
    )
    return (
        "Ты CAD-агент. Собираешь деталь по плану чертежа через core.\n"
        + _API
        + _LOGIC
        + (("\n## Память\n" + mem + "\n") if use_mem else "")
        + _RULES
        + "\n## Справка\n"
        + load_patterns()
    )


SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    return (
        "Собери деталь по ТЗ и BUILD_PLAN. "
        "Массивы → pattern_*. Пунктир не контур. "
        "Размеры эскиза (dim_*) желательны.\n\n"
        f"ТЗ:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Перепиши код по BUILD_PLAN. Только ```python.\n"
        f"Замечания:\n{err}\n\nТЗ:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
