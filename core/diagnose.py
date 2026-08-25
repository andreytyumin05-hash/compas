"""
Диагностика COM. Запуск: python -m core.diagnose
(КОМПАС должен быть открыт)
"""

from __future__ import annotations

import sys
import traceback


def main() -> None:
    print("=== КОМПАС COM diagnose ===\n")
    try:
        import pythoncom
        from win32com.client import GetActiveObject
        from win32com.client.dynamic import Dispatch as DynDispatch

        pythoncom.CoInitialize()
    except Exception as e:
        print("pywin32 FAIL:", e)
        sys.exit(1)
    print("pywin32: OK")

    for prog in ("Kompas.Application.5", "Kompas.Application.7"):
        print(f"\n--- {prog} ---")
        try:
            raw = GetActiveObject(prog)
            print("  GetActiveObject: OK")
        except Exception as e:
            print(f"  GetActiveObject: {e}")
            try:
                raw = DynDispatch(prog)
                print("  DynDispatch: OK")
            except Exception as e2:
                print(f"  DynDispatch: {e2}")
                continue
        try:
            obj = DynDispatch(raw)
        except Exception:
            obj = raw

        for name in (
            "Visible",
            "Document3D",
            "ActiveDocument3D",
            "Documents",
            "ApplicationName",
        ):
            try:
                v = getattr(obj, name)
                print(f"  .{name}: getattr OK type={type(v)}")
                if name in ("Document3D", "ActiveDocument3D", "Documents"):
                    try:
                        r = v() if callable(v) else v
                        print(f"    call/use OK type={type(r)}")
                    except Exception as e:
                        print(f"    call/use FAIL: {e}")
            except Exception as e:
                print(f"  .{name}: FAIL {e}")

        if prog.endswith(".7"):
            try:
                docs = obj.Documents
                for label, fn in [
                    ("Add(4,True)", lambda: docs.Add(4, True)),
                    ("Add(1,True)", lambda: docs.Add(1, True)),
                    ("AddWithDefaultSettings(1,True)", lambda: docs.AddWithDefaultSettings(1, True)),
                ]:
                    try:
                        fn()
                        print(f"  Documents.{label}: OK")
                        break
                    except Exception as e:
                        print(f"  Documents.{label}: FAIL {e}")
            except Exception as e:
                print(f"  Documents tests: {e}")

    print("\n--- new_part_document ---")
    try:
        from core.connection import KompasApp

        app = KompasApp.connect()
        doc3d, part = app.new_part_document()
        print("  SUCCESS", type(doc3d), type(part))
    except Exception:
        traceback.print_exc()

    print("\n--- from_active (if user opened a Part) ---")
    try:
        from core import Part

        p = Part.from_active()
        print("  SUCCESS from_active", p)
    except Exception as e:
        print("  from_active FAIL:", e)

    print("\n=== end ===")


if __name__ == "__main__":
    main()
