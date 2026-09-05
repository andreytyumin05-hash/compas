"""Smoke размеров в КОМПАС. Запуск: python scripts/smoke_dims.py

Не вставляй код в PowerShell.
"""
from __future__ import annotations
import sys

def main() -> int:
    from core import Part
    print("DimSmoke…")
    part = Part.create("DimSmoke")
    with part.sketch("xy") as sk:
        sk.line(0, 0, 50, 0)
        ok = sk.dim_linear(0, 0, 50, 0)
        print("dim_linear ->", ok)
        sk.circle(0, 0, 20)
        ok2 = sk.dim_radial(0, 0, 20)
        print("dim_radial ->", ok2)
    part.update()
    print("Смотри эскиз в КОМПАС.")
    return 0 if (ok or ok2) else 2

if __name__ == "__main__":
    raise SystemExit(main())
