"""
Диагностика COM КОМПАС — по плану open_ai_solve + Grok.

  python -m core.diagnose

КОМПАС должен быть запущен.
Опционально: заранее Файл → Создать → Деталь (для теста from_active).
"""

from __future__ import annotations

import sys
import traceback
import platform


def _section(title: str) -> None:
    print(f"\n=== {title} ===")


def _env() -> None:
    _section("Environment")
    print("Python:", sys.version.replace("\n", " "))
    print("Architecture:", platform.architecture(), platform.machine())
    try:
        import struct

        print("Pointer bits:", struct.calcsize("P") * 8)
    except Exception as e:
        print("Pointer bits: FAIL", e)


def _raw_probe() -> None:
    _section("Raw GetActiveObject (no DynDispatch wrap)")
    import pythoncom
    from win32com.client import GetActiveObject

    pythoncom.CoInitialize()

    for prog in ("Kompas.Application.5", "Kompas.Application.7"):
        print(f"\n--- {prog} ---")
        try:
            obj = GetActiveObject(prog)
            print("  GetActiveObject OK", type(obj))
        except Exception as e:
            print("  GetActiveObject FAIL", e)
            continue

        for name in ("Visible", "Document3D", "ActiveDocument3D", "Documents"):
            try:
                v = getattr(obj, name)
                print(f"  getattr.{name}: OK type={type(v)} repr={v!r}"[:120])
            except Exception as e:
                print(f"  getattr.{name}: FAIL {e}")

        if prog.endswith(".7"):
            try:
                docs = obj.Documents
                print("  Documents object:", type(docs), docs)
                for meth in ("Add", "AddWithDefaultSettings", "Count", "Item"):
                    attr = getattr(docs, meth, "__MISSING__")
                    print(f"  Documents.{meth}: {attr!r} type={type(attr)}")
                # real calls
                for label, fn in [
                    ("Add(4, True)", lambda: docs.Add(4, True)),
                    ("Add(1, True)", lambda: docs.Add(1, True)),
                    (
                        "AddWithDefaultSettings(1, True)",
                        lambda: docs.AddWithDefaultSettings(1, True),
                    ),
                ]:
                    try:
                        r = fn()
                        print(f"  CALL {label}: OK → {type(r)}")
                        break
                    except Exception as e:
                        print(f"  CALL {label}: FAIL {e}")
            except Exception as e:
                print("  Documents block FAIL", e)

        if prog.endswith(".5"):
            try:
                # call Document3D()
                try:
                    d = obj.Document3D()
                    print("  CALL Document3D(): OK", type(d))
                    try:
                        d.Create(False, True)
                        print("  CALL Create(False,True): OK")
                        try:
                            p = d.GetPart(-1)
                            print("  CALL GetPart(-1): OK", type(p))
                        except Exception as e:
                            print("  CALL GetPart(-1): FAIL", e)
                    except Exception as e:
                        print("  CALL Create: FAIL", e)
                except Exception as e:
                    print("  CALL Document3D(): FAIL", e)
            except Exception as e:
                print("  App5 doc block FAIL", e)


def _dynamic_probe() -> None:
    _section("A/B Test A — dynamic.Dispatch wrap")
    from win32com.client import GetActiveObject
    from win32com.client.dynamic import Dispatch as DynDispatch

    try:
        raw = GetActiveObject("Kompas.Application.7")
        obj = DynDispatch(raw)
        docs = obj.Documents
        print("dyn Documents:", type(docs))
        print("dyn Add attr:", getattr(docs, "Add", None))
        try:
            docs.Add(4, True)
            print("dyn Add(4,True): OK")
        except Exception as e:
            print("dyn Add(4,True): FAIL", e)
    except Exception as e:
        print("dynamic probe FAIL", e)


def _gencache_probe() -> None:
    _section("A/B Test B — gencache / EnsureModule (may fail on makepy)")
    import pythoncom
    from win32com.client import GetActiveObject, gencache, Dispatch

    # API7 typelib GUID used across KOMPAS installs
    api7_guid = "{69AC2981-37C0-4379-84FD-5DD2F3C0A520}"
    api5_guid = "{0422828C-F174-495E-AC5D-D31014DBBE87}"

    try:
        raw7 = GetActiveObject("Kompas.Application.7")
        mod7 = gencache.EnsureModule(api7_guid, 0, 1, 0)
        print("EnsureModule API7: OK", mod7)
        try:
            app = mod7.IApplication(
                raw7._oleobj_.QueryInterface(
                    mod7.IApplication.CLSID, pythoncom.IID_IDispatch
                )
            )
            print("IApplication QI: OK", type(app))
            try:
                docs = app.Documents
                print("typed Documents:", type(docs))
                r = docs.Add(4, True)
                print("typed Add(4,True): OK", type(r))
            except Exception as e:
                print("typed Documents/Add FAIL", e)
        except Exception as e:
            print("IApplication QI FAIL", e)
    except Exception as e:
        print("gencache API7 path FAIL", e)

    try:
        raw5 = GetActiveObject("Kompas.Application.5")
        mod5 = gencache.EnsureModule(api5_guid, 0, 1, 0)
        print("EnsureModule API5: OK")
        try:
            kobj = mod5.KompasObject(
                raw5._oleobj_.QueryInterface(
                    mod5.KompasObject.CLSID, pythoncom.IID_IDispatch
                )
            )
            print("KompasObject QI: OK", type(kobj))
            try:
                d = kobj.Document3D()
                print("typed Document3D(): OK", type(d))
            except Exception as e:
                print("typed Document3D() FAIL", e)
        except Exception as e:
            print("KompasObject QI FAIL", e)
    except Exception as e:
        print("gencache API5 path FAIL", e)


def _wrapper_tests() -> None:
    _section("core.KompasApp.new_part_document")
    try:
        from core.connection import KompasApp

        app = KompasApp.connect()
        doc, part = app.new_part_document()
        print("SUCCESS new_part_document", type(doc), type(part))
    except Exception:
        traceback.print_exc()

    _section("Part.from_active (need open Part in UI)")
    try:
        from core import Part

        p = Part.from_active()
        print("SUCCESS from_active", p)
    except Exception as e:
        print("from_active FAIL:", e)


def main() -> None:
    print("compas COM diagnose (open_ai_solve plan)")
    _env()
    try:
        import pythoncom
        from win32com.client import GetActiveObject  # noqa: F401

        pythoncom.CoInitialize()
        print("\npywin32: OK")
    except Exception as e:
        print("pywin32 FAIL", e)
        sys.exit(1)

    _raw_probe()
    _dynamic_probe()
    _gencache_probe()
    _wrapper_tests()
    print("\n=== end diagnose ===")
    print("Next: if from_active works, run: python -m core.smoke_active")


if __name__ == "__main__":
    main()
