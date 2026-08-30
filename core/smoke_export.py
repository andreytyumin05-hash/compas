"""
Проверка SaveAs .m3d / .step и close.

  python -m core.smoke_export
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    from core import Part
    from core.export import session_dir, safe_delete_path

    print("smoke_export — КОМПАС открыт")
    part = Part.create("SmokeExport")
    with part.sketch("xy") as sk:
        sk.circle(0, 0, 15)
    part.extrude(sk, depth=20)
    part.update()

    d = session_dir("smoke_export")
    try:
        paths = part.export_formats(d, formats=["m3d", "step"], close=True)
        for p in paths:
            print(f"OK {p} size={p.stat().st_size}")
        if not paths:
            print("FAIL: no files")
            sys.exit(1)
        print("OK export+close")
    except Exception as e:
        print(f"FAIL: {e}")
        sys.exit(1)
    finally:
        safe_delete_path(d)


if __name__ == "__main__":
    main()
