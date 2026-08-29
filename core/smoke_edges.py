"""
Ручные smoke-тесты выбора рёбер и фаски/скругления.

КОМПАС должен быть запущен. Лог пишется в stdout — приложи к PR.

  python -m core.smoke_edges
  python -m core.smoke_edges cube
  python -m core.smoke_edges bushing
  python -m core.smoke_edges plate
"""

from __future__ import annotations

import sys
import traceback
from typing import Callable, List, Tuple


def _log(msg: str) -> None:
    print(msg, flush=True)


def _run(name: str, fn: Callable[[], None]) -> bool:
    _log(f"\n=== TEST: {name} ===")
    try:
        fn()
        _log(f"OK: {name}")
        return True
    except Exception as e:
        _log(f"FAIL: {name}: {e}")
        traceback.print_exc()
        return False


def test_cube_fillet_all() -> None:
    """Куб 40³ — скругление всех рёбер R=2."""
    from core import Part

    part = Part.create("SmokeCube")
    with part.sketch("xy") as sk:
        sk.rectangle(-20, -20, 40, 40)
    part.extrude(sk, depth=40)
    edges = part.get_edges("all")
    _log(f"  edges collected: {len(edges)} filter={edges.filter_name}")
    for i, e in enumerate(list(edges)[:5]):
        _log(f"  edge[{i}] src={e.source} mid={e.midpoint} dir={e.direction}")
    part.fillet(edges, radius=2.0)
    part.update()
    _log("  fillet applied — проверь визуально в КОМПАС")


def test_cube_chamfer_all() -> None:
    from core import Part

    part = Part.create("SmokeCubeChamfer")
    with part.sketch("xy") as sk:
        sk.rectangle(0, 0, 30, 30)
    part.extrude(sk, depth=30)
    edges = part.get_edges("all")
    _log(f"  edges: {len(edges)}")
    part.chamfer(edges, distance=1.5)
    part.update()


def test_bushing_outer_edges() -> None:
    """Втулка Ø40/Ø20 L=50 — фаска на всех доступных рёбрах 0.5."""
    from core import Part

    part = Part.create("SmokeBushing")
    with part.sketch("xy") as sk:
        sk.circle(0, 0, 20)
    part.extrude(sk, depth=50)
    part.hole(0, 0, diameter=20, through_all=True)
    edges = part.get_edges("all")
    _log(f"  edges after hole: {len(edges)}")
    # фильтры parallel_* могут не сработать без direction — честно логируем
    try:
        ez = part.get_edges("parallel_z")
        _log(f"  parallel_z: {len(ez)}")
        part.chamfer(ez, distance=0.5)
    except Exception as e:
        _log(f"  parallel_z unavailable (expected on some installs): {e}")
        part.chamfer(edges, distance=0.5)
    part.update()


def test_plate_fillet() -> None:
    """Плита 80×50×8 с отверстием — fillet all R=1."""
    from core import Part

    part = Part.create("SmokePlate")
    with part.sketch("xy") as sk:
        sk.rectangle(0, 0, 80, 50)
    part.extrude(sk, depth=8)
    part.hole(40, 25, diameter=10, through_all=True)
    edges = part.get_edges("all")
    _log(f"  edges: {len(edges)}")
    try:
        top = part.get_edges("top_z", tol=0.5)
        _log(f"  top_z: {len(top)}")
        part.fillet(top, radius=1.0)
    except Exception as e:
        _log(f"  top_z fallback to all: {e}")
        part.fillet(edges, radius=1.0)
    part.update()


TESTS = {
    "cube": test_cube_fillet_all,
    "chamfer": test_cube_chamfer_all,
    "bushing": test_bushing_outer_edges,
    "plate": test_plate_fillet,
}


def main() -> None:
    names = sys.argv[1:] or list(TESTS.keys())
    _log("smoke_edges — КОМПАС должен быть запущен")
    ok = 0
    for name in names:
        fn = TESTS.get(name)
        if not fn:
            _log(f"unknown test {name}, known: {list(TESTS)}")
            continue
        if _run(name, fn):
            ok += 1
    _log(f"\nPassed {ok}/{len(names)}")
    sys.exit(0 if ok == len(names) else 1)


if __name__ == "__main__":
    main()
