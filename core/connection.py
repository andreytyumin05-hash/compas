"""
Подключение к КОМПАС-3D (API5/API7 late binding).

Runtime-critical COM calls are intentionally late-bound because the local
installation may not have a registered typelib.
"""

from __future__ import annotations

from typing import Any, Optional, Tuple, List

try:
    import pythoncom
except ImportError:
    pythoncom = None  # type: ignore[assignment]

try:
    from win32com.client import Dispatch, GetActiveObject
except ImportError as e:
    raise ImportError("pip install pywin32") from e

P_TOP_PART = -1
O3D_PLANE_XOY = 1
O3D_PLANE_XOZ = 2
O3D_PLANE_YOZ = 3
O3D_SKETCH = 5
O3D_BASE_EXTRUSION = 24
O3D_BOSS_EXTRUSION = 25
O3D_CUT_EXTRUSION = 26
O3D_BASE_ROTATED = 27
O3D_BOSS_ROTATED = 28
O3D_CUT_ROTATED = 29
DT_NORMAL = 0
DT_REVERSE = 1
DT_BOTH = 2
ET_BLIND = 0
ET_THROUGH_ALL = 1
KS_DOCUMENT_PART = 4


def _co_init() -> None:
    if pythoncom is not None:
        try:
            pythoncom.CoInitialize()
        except Exception:
            pass


def _dyn(prog_id: str) -> Any:
    _co_init()
    try:
        return GetActiveObject(prog_id)
    except Exception:
        return Dispatch(prog_id)


def _as_prop_or_call(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception as e:
        raise AttributeError(f"{name}: {e}") from e


def _is_legacy_part(part: Any) -> bool:
    try:
        return callable(getattr(part, "NewEntity"))
    except Exception:
        return False


def _extract_part(doc: Any, *, require_legacy_part: bool = False) -> Tuple[Optional[Any], str]:
    if doc is None:
        return None, "doc is None"
    notes: List[str] = []
    for attr in ("TopPart", "topPart", "Part", "part"):
        try:
            p = getattr(doc, attr)
            if p is not None:
                if not require_legacy_part or _is_legacy_part(p):
                    return p, f"doc.{attr}"
                notes.append(f"{attr}=API7 part")
        except Exception as e:
            notes.append(f"{attr}:{e}")
    for method in ("GetTopPart", "get_TopPart"):
        try:
            p = getattr(doc, method)()
            if p is not None:
                if not require_legacy_part or _is_legacy_part(p):
                    return p, f"{method}()"
                notes.append(f"{method}()=API7 part")
        except Exception as e:
            notes.append(f"{method}():{e}")
    for args in ((-1,), (P_TOP_PART,), (0,)):
        try:
            p = doc.GetPart(*args)
            if p is not None:
                if not require_legacy_part or _is_legacy_part(p):
                    return p, f"GetPart{args}"
        except Exception as e:
            notes.append(f"GetPart{args}:{e}")
    for name in ("Document3D", "ActiveDocument3D"):
        try:
            inner = _as_prop_or_call(doc, name)
            if inner is not None and inner is not doc:
                p, how = _extract_part(inner, require_legacy_part=require_legacy_part)
                if p is not None:
                    return p, f"{name}->{how}"
        except Exception as e:
            notes.append(f"{name}:{e}")
    return None, "; ".join(notes)


class KompasApp:
    def __init__(self, k5: Any, app7: Optional[Any]):
        self.k5 = k5
        self.app7 = app7

    @classmethod
    def connect(cls) -> "KompasApp":
        k5 = app7 = None
        err5 = err7 = None
        try:
            k5 = _dyn("Kompas.Application.5")
        except Exception as e:
            err5 = e
        try:
            app7 = _dyn("KOMPAS.Application.7")
        except Exception as e:
            err7 = e
        if k5 is None and app7 is None:
            raise RuntimeError(f"КОМПАС не доступен: API5={err5}; API7={err7}")
        return cls(k5, app7)

    def hide_messages(self, hide: bool = True) -> None:
        for obj in (self.k5, self.app7):
            if obj is None:
                continue
            for name in ("Visible", "HideMessages"):
                try:
                    setattr(obj, name, not hide if name == "Visible" else hide)
                except Exception:
                    pass

    def new_part_document(self) -> Tuple[Any, Any]:
        self._ensure_app7()
        try:
            docs = self.app7.Documents
            doc = docs.Add(KS_DOCUMENT_PART, True)
        except Exception as e:
            raise RuntimeError(f"Documents.Add({KS_DOCUMENT_PART}, True): {e}") from e
        part, how = _extract_part(doc, require_legacy_part=True)
        if part is None:
            raise RuntimeError(f"Не удалось получить ksPart: {how}")
        return doc, part

    def _ensure_app7(self) -> None:
        if self.app7 is None:
            raise RuntimeError("API7 KOMPAS недоступен")


def get_app(*, auto_launch: bool = True) -> KompasApp:
    if not auto_launch:
        return KompasApp.connect()
    return KompasApp.connect()
