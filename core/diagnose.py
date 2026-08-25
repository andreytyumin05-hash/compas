"""
Диагностика COM КОМПАС.

  python -m core.diagnose
"""

from __future__ import annotations

import sys
import traceback


def main() -> None:
    print("=== Диагностика КОМПАС COM ===\n")

    try:
        import pythoncom
        from win32com.client import Dispatch, GetActiveObject, gencache

        pythoncom.CoInitialize()
    except Exception as e:
        print(f"pywin32: FAIL — {e}")
        sys.exit(1)
    print("pywin32: OK")

    for prog in ("Kompas.Application.5", "Kompas.Application.7"):
        print(f"\n--- {prog} ---")
        obj = None
        try:
            obj = GetActiveObject(prog)
            print("  GetActiveObject: OK")
        except Exception as e:
            print(f"  GetActiveObject: {e}")
            try:
                obj = Dispatch(prog)
                print("  Dispatch: OK")
            except Exception as e2:
                print(f"  Dispatch: {e2}")
                continue

        for name in ("Visible", "Document3D", "ActiveDocument3D", "Documents", "ApplicationName"):
            try:
                v = getattr(obj, name)
                print(f"  .{name}: OK → {type(v)}")
            except Exception as e:
                print(f"  .{name}: FAIL — {e}")

    print("\n--- KompasObject via typelib ---")
    try:
        from core.connection import _get_kompas_object

        k5 = _get_kompas_object()
        print(f"  type: {type(k5)}")
        for name in ("Document3D", "ActiveDocument3D", "Visible"):
            try:
                v = getattr(k5, name)
                print(f"  .{name}: OK → {type(v)}")
            except Exception as e:
                print(f"  .{name}: FAIL — {e}")

        print("\n--- new_part_document ---")
        from core.connection import KompasApp

        app = KompasApp.connect()
        doc3d, part = app.new_part_document()
        print(f"  doc3d: {type(doc3d)}")
        print(f"  part:  {type(part)}")
        print("  SUCCESS — деталь создана")
    except Exception:
        print("  FAIL:")
        traceback.print_exc()

    print("\n=== конец ===")


if __name__ == "__main__":
    main()
