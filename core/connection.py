"""
Подключение к КОМПАС-3D (runtime facts 2026-08-25 diagnose):

PROVEN:
- Python 3.14 x64, pywin32 OK
- GetActiveObject App5 + App7 OK
- app7.Documents.Add(4, True) OK
- gencache EnsureModule FAIL на части машин
- ActiveDocument3D / Document3D — property, not method

Strategy:
1) Create part with app7.Documents.Add(4, True)
2) Extract ksPart from returned document
3) Never rely on gencache alone
"""

from __future__ import annotations

from typing import Any, Optional, Tuple, List

from .exceptions import KompasNotRunningError, KompasError

try:
    import pythoncom
    from win32com.client import Dispatch, GetActiveObject

    _HAS_COM = True
except ImportError:
    pythoncom = None  # type: ignore
    Dispatch = None  # type: ignore
    GetActiveObject = None  # type: ignore
    _HAS_COM = False

P_TOP_PART = -1
O3D_PLANE_XOY = 1
O3D_PLANE_XOZ = 2
O3D_PLANE_YOZ = 3
O3D_SKETCH = 5
O3D_BASE_EXTRUSION = 24
O3D_BOSS_EXTRUSION = 25
O3D_CUT_EXTRUSION = 26
O3D_BOSS_ROTATED = 27
DT_NORMAL = 0


def _as_prop_or_call(obj: Any, name: str) -> Any:
    try:
        v = getattr(obj, name)
    except Exception:
        return None
    if v is None:
        return None
    if callable(v):
        try:
            return v()
        except Exception:
            return v
    return v


def _extract_part(doc: Any, require_legacy_part: bool = True) -> Tuple[Any, str]:
    if doc is None:
        return None, "doc is None"
    for attr in ("TopPart", "topPart", "GetPart", "Part"):
        try:
            v = getattr(doc, attr, None)
            if v is None:
                continue
            part = v() if callable(v) else v
            if part is not None:
                return part, attr
        except Exception as e:
            continue
    try:
        p = doc.GetPart(P_TOP_PART)
        if p is not None:
            return p, "GetPart(-1)"
    except Exception:
        pass
    return None, "part not found"


class KompasApp:
    def __init__(self) -> None:
        if not _HAS_COM:
            raise KompasNotRunningError("pywin32/pythoncom не установлены")
        self.app7 = None
        self.k5 = None
        self._connect()

    def _connect(self) -> None:
        assert pythoncom is not None
        pythoncom.CoInitialize()
        for prog in ("Kompas.Application.7", "Kompas.Application.5"):
            try:
                obj = GetActiveObject(prog)
                if "7" in prog:
                    self.app7 = obj
                else:
                    self.k5 = obj
            except Exception:
                try:
                    obj = Dispatch(prog)
                    if "7" in prog:
                        self.app7 = obj
                    else:
                        self.k5 = obj
                except Exception:
                    continue
        if self.app7 is None and self.k5 is None:
            raise KompasNotRunningError("КОМПАС не запущен / не установлен")

    def hide_messages(self, hide: bool = True) -> None:
        for app in (self.app7, self.k5):
            if app is None:
                continue
            for attr in ("HideMessage", "hideMessage"):
                try:
                    setattr(app, attr, 1 if hide else 0)
                except Exception:
                    pass

    def new_part_document(self) -> Tuple[Any, Any]:
        if self.app7 is not None:
            try:
                docs = self.app7.Documents
                doc = docs.Add(4, True)
                part, how = _extract_part(doc)
                if part is not None:
                    return doc, part
            except Exception as e:
                last = e
        raise KompasError(f"Не удалось создать деталь: {locals().get('last', 'unknown')}")


def get_app(auto_launch: bool = True) -> KompasApp:
    if not _HAS_COM:
        raise KompasNotRunningError(
            "pywin32/pythoncom не установлены (только Windows+КОМПАС)"
        )
    return KompasApp()
