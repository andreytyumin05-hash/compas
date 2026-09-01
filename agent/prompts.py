"""Кодоген: BUILD_PLAN + stadium/boss/counterbore + visual top/iso."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = '''
## API core (пишите ТОЛЬКО эти методы)

```python
from core import Part
part = Part.create("Имя")
part.var("L", 116, comment="длина")
part.var("W", 80, comment="ширина")
part.var("T", 13, comment="толщина фланца")

# Эскиз: stadium = «капсула» (прямоугольник + полукруги), НЕ rectangle для овальной крышки
with part.sketch("xy") as sk:
    sk.stadium(-58, -40, 116, 80)   # x,y = левый-нижний угол, length, width
    # или sk.rounded_rect(x, y, length, width, radius=R)
    # sk.circle(xc, yc, radius)  # radius = Ø/2
part.extrude(sk, depth=13)          # фланец / база

# Бобышка стадион/круг на той же плоскости (вторая ступень вверх)
with part.sketch("xy") as sk2:
    sk2.stadium(-30, -25, 60, 50)   # пример — берите размеры из BUILD_PLAN
part.extrude(sk2, depth=18)         # высота бобышки ОТ плоскости фланца

# Отверстия: всегда hole / pattern / counterbore, не «забывать»
part.hole(-18, 0, diameter=28, through_all=True)
part.hole(18, 0, diameter=28, through_all=True)
# цековка: pilot сквозной + расточка depth
part.counterbore(x, y, pilot_diameter=7, counterbore_diameter=11, counterbore_depth=6, through_all=True)
part.pattern_holes_circular((0,0), pcd=70, count=6, diameter=7)  # только если одинаковые без цековки
part.pattern_holes_points([(x,y),...], diameter=5)  # штифты по координатам

part.set_properties(name="Крышка", designation="...")
part.update()
# Виды для ПЛОСКОЙ крышки: top (отверстия видны) + iso — НЕ side
part.set_view("top")
part.screenshot("_top.png")
part.set_view("iso")
part.screenshot("_iso.png")
```
'''

_LOGIC = '''
## Правила геометрии (критично)

1. Следуй BUILD_PLAN по порядку. Не выбрасывай отверстия и цековки.
2. Крышка/фланец овальные → sk.stadium или rounded_rect. ЗАПРЕЩЕНО одно rectangle «коробкой».
3. База (фланец) extrude на thickness; бобышка — ОТДЕЛЬНЫЙ sketch+extrude на height бобышки.
4. Два Ø28 с шагом 36 → два hole на x=±18 (или как в плане), не один.
5. Цековка Ø7/Ø11 depth 6 → counterbore(...), не просто hole(7).
6. 6 крепежных по контуру — либо 6× counterbore с координатами, либо pattern + отдельно цековки если API позволяет.
7. Пунктир/оси на чертеже ≠ наружный контур.
8. В конце set_view("top") и set_view("iso") + screenshot — чтобы были видны отверстия сверху.
9. Числа только из ТЗ/плана; не упрощай «примерно плита 100×80».
'''

_RULES = '''
Сначала 4–8 строк плана (эхо BUILD_PLAN), затем один блок ```python
с from core import Part и part.update(). Без win32com/loft/sweep.
Если в ТЗ есть stadium/овал/капсула — в коде обязан быть stadium или rounded_rect.
Если есть цековка — обязан counterbore.
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    use_mem = mem and not any(
        w in (task or "").lower()
        for w in (
            "build_plan",
            "ступен",
            "пробк",
            "вал",
            "feature=",
            "body_style",
            "крышк",
            "stadium",
            "цеков",
            "бобыш",
        )
    )
    return (
        "Ты CAD-агент КОМПАС. Строишь деталь ТОЧНО по плану, без упрощений.\n"
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
        "Собери деталь СТРОГО по ТЗ и BUILD_PLAN. Не заменяй stadium на rectangle.\n"
        "Все отверстия и цековки из плана обязательны.\n"
        "В конце: set_view top + iso и screenshot.\n\n"
        f"ТЗ:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Перепиши код. Сохрани stadium/boss/counterbore из плана. "
        "Не упрощать до одной плиты. Только ```python.\n"
        f"Замечания:\n{err}\n\nТЗ:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
