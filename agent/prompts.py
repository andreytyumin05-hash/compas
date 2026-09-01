"""Кодоген: BUILD_PLAN + core API + visual loop (Habr)."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = '''
## API core

```python
from core import Part
part = Part.create("Имя")
# переменные с человеческими именами (как в параметрике инженера)
part.var("D", 40, comment="наружный Ø")
part.var("d", 20, comment="внутренний Ø")
part.var("L", 50, comment="длина")
with part.sketch("xy") as sk:  # xy|xz|yz
    sk.circle(xc, yc, radius)           # radius = Ø/2; можно D/2 через число
    sk.rectangle(x, y, w, h)
    sk.rounded_rect(...); sk.stadium(...)
    sk.polygon([(x,y),...])
    sk.dim_radial(xc, yc, radius)       # best-effort
    sk.dim_linear(x1, y1, x2, y2)
part.extrude(sk, depth=H)
part.cut(sk, depth=D)                  # глухой
part.cut(sk, through_all=True)
part.hole(x, y, diameter=D, through_all=True)
part.pattern_holes_circular((0,0), pcd=P, count=N, diameter=D)
part.boss(x, y, diameter=D, height=H)
part.pocket(x, y, diameter=D, depth=H)
part.ring_groove(x, y, outer_diameter=..., inner_diameter=..., depth=...)
part.counterbore(...); part.countersink(...)
part.slot(...); part.keyway(...)
edges = part.get_edges("all")
part.fillet(edges, radius=r)
part.chamfer(edges, distance=d)
part.set_properties(name="...", designation="...", material="Сталь 45")
part.update()
# visual loop (обязательно для сложных; желательно всегда)
part.set_view("iso")
part.screenshot("preview_iso.png")
part.set_view("front")
part.screenshot("preview_front.png")
```
'''

_LOGIC = '''
## Как рассуждать (Habr + MCP)

1. BUILD_PLAN — по шагам, ничего не выкидывать.
2. Пунктир/оси — не наружный контур.
3. Одинаковые отверстия по кругу → pattern_holes_circular.
4. Ступени: circle + extrude; не один rectangle.
5. Карман/шестигранник: polygon/pocket + cut(depth=...).
6. Цековка → counterbore; канавка → ring_groove; фаски в конце.
7. Ключевые размеры → part.var("D", ..., comment="...") до эскизов.
8. После геометрии → set_properties, затем update, затем visual loop (≥2 вида).
9. LLM плохо «видит» 3D по коду: скриншоты обязательны для проверки инженером/VLM.
10. Чертежи с несколькими видами — не упрощать до одной плиты.
'''

_RULES = '''
Сначала 3–6 строк плана, затем один блок ```python
с from core import Part, var, properties, update, screenshot.
Без win32com/loft/sweep. Один связный скрипт сильнее кучи атомарных tools.
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    use_mem = mem and not any(
        w in (task or "").lower()
        for w in ("build_plan", "ступен", "пробк", "вал", "feature=", "body_style")
    )
    return (
        "Ты CAD-агент КОМПАС. Пишешь короткий Python через core (как Habr-агент).\n"
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
        "Собери деталь по ТЗ и BUILD_PLAN.\n"
        "Обязательно по возможности: part.var, set_properties, set_view+screenshot (iso и front).\n"
        "Массивы → pattern_*. Пунктир не контур.\n\n"
        f"ТЗ:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Перепиши код по BUILD_PLAN. Добавь var/properties/visual loop если их не было.\n"
        "Только ```python.\n"
        f"Замечания:\n{err}\n\nТЗ:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
