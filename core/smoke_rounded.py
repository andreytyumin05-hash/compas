"""python -m core.smoke_rounded — проверка rounded_rect / stadium в КОМПАС."""

from __future__ import annotations

import sys


def main() -> None:
    from core import Part

    print("smoke_rounded — КОМПАС открыт")
    part = Part.create("SmokeRounded")
    with part.sketch("xy") as sk:
        sk.rounded_rect(-58, -40, 116, 80, radius=40)
    part.extrude(sk, depth=13)
    with part.sketch("xy") as sk2:
        sk2.circle(0, 0, 30)
    part.extrude(sk2, depth=18)
    part.update()
    print("OK: stadium 116x80 R40 + boss R30 h18")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)
