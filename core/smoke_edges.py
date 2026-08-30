"""
Smoke-тесты рёбер / фаски / скругления (КОМПАС v23).

  python -m core.smoke_edges
  python -m core.smoke_edges cube
"""

from __future__ import annotations

import sys
import traceback
from typing import Callable


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
    from core import Part

    part = Part.create("SmokeCube")
    with part.sketch("xy") as sk:
        sk.rectangle(-20, -20, 40, 40)
    part.extrude(sk, depth=40)
    edges = part.get_edges("all")
    _log(f"  edges: {len(edges)} filter={edges.filter_name}")
    for i, e in enumerate(list(edges)[:3]):
        _log(f"  edge[{i}] src={e.source}")
    if len(edges) == 0:
        raise RuntimeError("0 рёбер — EntityCollection(7) пуст")
    # куб: ожидаем 12 рёбер (не 20 вершин/мусор)
    _log(f"  (для куба типично 12 рёбер, сейчас {len(edges)})")
    part.fillet(edges, radius=2.0)
    part.update()


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


def test_bushing() -> None:
    from core import Part

    part = Part.create("SmokeBushing")
    with part.sketch("xy") as sk:
        sk.circle(0, 0, 20)
    part.extrude(sk, depth=50)
    part.hole(0, 0, diameter=20, through_all=True)
    edges = part.get_edges("all")
    _log(f"  edges after hole: {len(edges)}")
    # точка на наружном верхнем ободе ~ (20, 0, 50)
    try:
        near = part.get_edges("near_point", point=(20.0, 0.0, 50.0))
        _log(f"  near_point top rim: {len(near)}")
        part.chamfer(near, distance=0.5)
    except Exception as e:
        _log(f"  near_point fallback all: {e}")
        part.chamfer(edges, distance=0.5)
    part.update()


def test_plate() -> None:
    from core import Part

    part = Part.create("SmokePlate")
    with part.sketch("xy") as sk:
        sk.rectangle(0, 0, 80, 50)
    part.extrude(sk, depth=8)
    part.hole(40, 25, diameter=10, through_all=True)
    edges = part.get_edges("all")
    _log(f"  edges: {len(edges)}")
    part.fillet(edges, radius=1.0)
    part.update()


TESTS = {
    "cube": test_cube_fillet_all,
    "chamfer": test_cube_chamfer_all,
    "bushing": test_bushing,
    "plate": test_plate,
}


def main() -> None:
    names = sys.argv[1:] or list(TESTS.keys())
    _log("smoke_edges — КОМПАС запущен, v23")
    ok = 0
    for name in names:
        fn = TESTS.get(name)
        if not fn:
            _log(f"unknown: {name}")
            continue
        if _run(name, fn):
            ok += 1
    _log(f"\nPassed {ok}/{len(names)}")
    sys.exit(0 if ok == len(names) else 1)


if __name__ == "__main__":
    main()
