"""Smoke размеров в КОМПАС.

  python scripts/smoke_dims.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def main() -> int:
    from core import Part
    from core.sketch_dims import _kompas_object, _init_param, _KO_LDIM

    print("DimSmoke…")
    part = Part.create("DimSmoke")
    with part.sketch("xy") as sk:
        ko = _kompas_object(sk)
        print("k5 GetParamStruct:", bool(ko and callable(getattr(ko, "GetParamStruct", None))))
        param = _init_param(ko, _KO_LDIM)
        print("GetParamStruct(45):", type(param).__name__ if param is not None else None)
        if param is not None:
            for name in ("GetSPar", "GetDPar", "GetTPar"):
                g = getattr(param, name, None)
                try:
                    v = g() if callable(g) else g
                    print(f"  {name}:", type(v).__name__ if v is not None else None)
                except Exception as e:
                    print(f"  {name}: ERR {e}")

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
