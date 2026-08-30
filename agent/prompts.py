"""Промпт: дерево фич для сложных деталей."""

from .knowledge import load_patterns
from .memory import few_shot_from_memory

_API = '''
## API core (только эти методы)

```python
from core import Part
part = Part.create("Имя")
with part.sketch("xy") as sk:  # xy | xz | yz
    sk.circle(xc, yc, radius)
    sk.rectangle(x, y, w, h)
    sk.rounded_rect(x, y, w, h, radius=R)
    sk.stadium(x, y, length, width)
    sk.ellipse / sk.line / sk.polygon / sk.polyline / sk.slot / sk.spline / sk.arc_by_points
part.extrude(sk, depth=H)                    # база или бобышка (второе+)
part.cut(sk, depth=D)                        # глухой карман
part.cut(sk, through_all=True)               # сквозной вырез
part.hole(x, y, diameter=D, through_all=True)
part.hole(x, y, diameter=D, depth=H)         # глухое, если API поддерживает depth
part.pattern_holes_circular((0,0), pcd=P, count=N, diameter=D)
part.pattern_holes_rect(x1,y1,x2,y2, diameter=D)
part.pattern_holes_points([(x1,y1), (x2,y2)], diameter=D)
part.pattern_holes_linear((x0,y0), count=N, step=S, diameter=D, direction=(1,0))
part.boss(x, y, diameter=D, height=H)
part.hex_boss(x, y, diameter=D, height=H)
part.pocket(x, y, diameter=D, depth=H)
part.groove(x, y, outer_diameter=D2, inner_diameter=D1, depth=H)
part.keyway(x, y, length=L, width=W, depth=H, axis="x")
part.counterbore(x, y, pilot_diameter=D1, counterbore_diameter=D2, counterbore_depth=H)
part.countersink(x, y, pilot_diameter=D1, countersink_diameter=D2, depth=H)
part.slot(x1, y1, x2, y2, width=W, depth=H, through_all=True)
part.step(x, y, width=W, height=H, depth=D, shape="rect")
part.mirror_points(points, axis="x")
part.sketch_on_face("top", plane="xy")
part.shell(thickness=T)                     # контракт API; только если реально доступно в детале
part.thread(x, y, diameter=D, pitch=P, length=L, through_all=True)
part.sweep(profile, path)                    # контракт API; требует отдельную реализацию
part.loft([sk1, sk2, sk3])                  # контракт API; требует отдельную реализацию
edges = part.get_edges("all")
part.fillet(edges, radius=r)
part.chamfer(edges, distance=d)
part.fillet_edge(radius=r, filter="all")
part.chamfer_edge(distance=d, filter="all")
part.update()
```

Запрещено: win32com, loft, sweep, boolean, неизвестные методы, текст вместо кода.
ØD → circle radius D/2 или hole(diameter=D).
'''

_LOGIC = '''
## Логика сложной детали (обязательно)

Думай деревом построения, не одним эскизом:

1) БАЗА — один контур + extrude(толщина/высота основания)
2) СТУПЕНИ / БОБЫШКИ — отдельные sketch + extrude на том же или другом виде
3) КАРМАНЫ — sketch контура выборки + cut(depth=...) НЕ through_all
4) ОТВЕРСТИЯ — hole / pattern_*; зенковка ≈ сначала shallow cut/hole большего Ø, потом основной hole
5) УСТУПЫ / ПАЗЫ / СИММЕТРИЯ — step / slot / keyway / mirror_points при наличии конструктивных признаков
6) ВЫСТУПЫ И КАНАВКИ — hex_boss / boss / groove / ring_groove для шестигранников, шпоночных пазов и канавок, если задача явно про это
7) КРИВЫЕ И ПОВЕРХНОСТИ — spline / arc_by_points / sketch_on_face / sweep / loft как возможные базовые конструкции, если задаётся сложная форма
8) ОБРАБОТКИ — counterbore / countersink / thread / shell только когда требуется техническая операция, а не просто базовый корпус
9) КРОМКИ — fillet/chamfer в конце

Жёсткие правила:
- Не допускать "схлопывание" детали в одиночное тело без заявленных вторичных элементов.
- Если в ТЗ есть boss / step / pocket / slot / hole / fillet / chamfer / shell / thread, в коде должен быть отдельный блок для каждого элемента, когда это реально требуется.
- Нельзя выдавать только базовую основу, если в ТЗ явно есть карман, бобышка, отверстия или финишные кромки.
- Не смешивать контур базы и вырез в одном эскизе.
- Глухой вырез: cut(sk, depth=...), не through_all.
- Сквозное: through_all=True.
- Несколько уровней высоты = несколько extrude подряд.
- Плоскость: явно sketch("xy"|"xz"|"yz").
- Если есть несколько групп отверстий — генерируй pattern_holes_circular/rect, а не один общий circle.
- Скругления и фаски делаются ПОСЛЕ базового тела и всех вырезов.
'''

_RULES = '''
Формат ответа:
- 2–5 строк плана: База → … → Кромки
- один блок ```python с from core import Part и part.update()
- код с колонки 0, без пояснений внутри блока
'''


def get_system_prompt(task: str = "") -> str:
    mem = few_shot_from_memory(task) if task else ""
    return (
        "Ты инженер-конструктор КОМПАС. Пишешь только исполняемый код core.\n"
        + _API
        + _LOGIC
        + ("\n## Успешные прошлые сборки\n" + mem + "\n" if mem else "")
        + _RULES
        + "\n## Справка\n"
        + load_patterns()
    )


SYSTEM_PROMPT = get_system_prompt()


def build_user_prompt(task: str) -> str:
    return (
        "Построй деталь по ТЗ строго по дереву фич.\n"
        "Запрещено упрощать модель до одного базового тела, если есть boss/step/pocket/hole/fillet/chamfer.\n"
        "Сначала короткий план: База → Бобышки/ступени → Карманы → Отверстия → Кромки.\n"
        "Затем один блок ```python``` только с исполняемым кодом core.\n\n"
        f"ТЗ:\n{task.strip()}"
    )


def build_repair_prompt(task: str, bad_code: str, errors: list) -> str:
    err = "\n".join(f"- {e}" for e in errors) or "- ошибка"
    return (
        "Исправь под API core. Только ```python.\n"
        f"Ошибки:\n{err}\n\nТЗ:\n{task.strip()}\n\n"
        f"Было:\n```python\n{(bad_code or '')[:2500]}\n```\n"
    )
