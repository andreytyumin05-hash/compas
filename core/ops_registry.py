"""
Единый реестр CAD-операций core (источник истины для prompts / validate).

status:
  real        — геометрия через COM (нужна live-проверка v23)
  best_effort — COM-путь есть, успех не гарантирован
  unsupported — заглушка; генератору запрещено
  meta        — create/update/export
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, FrozenSet, List


@dataclass(frozen=True)
class OpSpec:
    name: str
    purpose: str
    status: str
    params: str = ""
    depends: str = ""
    checks: str = ""
    visual: str = ""


OPS: Dict[str, OpSpec] = {
    "create": OpSpec("create", "Новая деталь", "meta"),
    "from_active": OpSpec("from_active", "Активный документ", "meta"),
    "update": OpSpec("update", "Обновить модель", "meta"),
    "close": OpSpec("close", "Закрыть документ", "meta"),
    "export": OpSpec("export", "Сохранить файл", "meta"),
    "export_formats": OpSpec("export_formats", "Несколько форматов", "meta"),
    "mass_properties": OpSpec("mass_properties", "Масса/объём", "meta"),
    "get_edges": OpSpec("get_edges", "Набор рёбер", "best_effort"),
    "sketch": OpSpec("sketch", "Эскиз xy/xz/yz", "real"),
    "extrude": OpSpec("extrude", "Выдавливание", "real"),
    "cut": OpSpec("cut", "Вырез", "real"),
    "revolve": OpSpec("revolve", "Вращение", "best_effort"),
    "hole": OpSpec("hole", "Отверстие", "real"),
    "pattern_holes_circular": OpSpec("pattern_holes_circular", "Круговой массив", "real"),
    "pattern_holes_rect": OpSpec("pattern_holes_rect", "Отверстия по углам", "real"),
    "pattern_holes_points": OpSpec("pattern_holes_points", "Отверстия по точкам", "real"),
    "pattern_holes_linear": OpSpec("pattern_holes_linear", "Линейный массив", "real"),
    "hole_list": OpSpec("hole_list", "Список отверстий", "real"),
    "mirror_points": OpSpec("mirror_points", "Зеркало точек", "meta"),
    "boss": OpSpec("boss", "Бобышка", "real"),
    "hex_boss": OpSpec("hex_boss", "Шестигранная бобышка", "real"),
    "pocket": OpSpec("pocket", "Карман", "real"),
    "ring_groove": OpSpec("ring_groove", "Канавка", "real"),
    "groove": OpSpec("groove", "Alias ring_groove", "real"),
    "keyway": OpSpec("keyway", "Шпоночный паз", "real"),
    "slot": OpSpec("slot", "Паз", "real"),
    "step": OpSpec("step", "Уступ", "real"),
    "counterbore": OpSpec("counterbore", "Цековка", "real"),
    "countersink": OpSpec("countersink", "Зенковка", "real"),
    "fillet": OpSpec("fillet", "Скругление", "best_effort"),
    "chamfer": OpSpec("chamfer", "Фаска", "best_effort"),
    "fillet_edge": OpSpec("fillet_edge", "Скругление filter", "best_effort"),
    "chamfer_edge": OpSpec("chamfer_edge", "Фаска filter", "best_effort"),
    "shell": OpSpec("shell", "Оболочка", "unsupported"),
    "thread": OpSpec("thread", "Резьба", "unsupported"),
    "sweep": OpSpec("sweep", "По траектории", "unsupported"),
    "loft": OpSpec("loft", "По сечениям", "unsupported"),
    "sketch_on_face": OpSpec(
        "sketch_on_face", "Грань тела не реализована", "unsupported"
    ),
}


def allowed_part_methods() -> FrozenSet[str]:
    return frozenset(
        n for n, s in OPS.items() if s.status in ("real", "best_effort", "meta")
    )


def unsupported_part_methods() -> FrozenSet[str]:
    return frozenset(n for n, s in OPS.items() if s.status == "unsupported")


def is_allowed_for_generation(name: str) -> bool:
    s = OPS.get(name)
    if s is None:
        return False
    return s.status in ("real", "best_effort", "meta")


def prompt_api_block() -> str:
    return """## API core (только эти методы — registry)

```python
from core import Part
part = Part.create("Имя")
with part.sketch("xy") as sk:  # xy|xz|yz
    sk.circle(xc, yc, radius)          # radius = Ø/2
    sk.rectangle(x, y, w, h)
    sk.rounded_rect(...); sk.stadium(...)
    sk.polygon([(x,y),...])
part.extrude(sk, depth=H)
part.cut(sk, depth=D)
part.cut(sk, through_all=True)
part.hole(x, y, diameter=D, through_all=True)
part.pattern_holes_circular((0,0), pcd=P, count=N, diameter=D)
part.pattern_holes_linear(start, count, step, diameter=D)
part.pattern_holes_points([(x,y),...], diameter=D)
part.boss(x, y, diameter=D, height=H)
part.pocket(x, y, diameter=D, depth=H)
part.ring_groove(x, y, outer_diameter=..., inner_diameter=..., depth=...)
part.counterbore(x, y, pilot_diameter=..., counterbore_diameter=..., counterbore_depth=..., through_all=True)
part.slot(...); part.step(...); part.keyway(...)
edges = part.get_edges("all")
part.fillet(edges, radius=r)
part.chamfer(edges, distance=d)
part.update()
```

ЗАПРЕЩЕНО: shell, thread, sweep, loft, sketch_on_face, win32com.
ØD → radius D/2 или hole(diameter=D)."""


def list_ops_by_status(status: str) -> List[str]:
    return sorted(n for n, s in OPS.items() if s.status == status)
