"""Подключение к КОМПАС-3D. Soft-import pywin32 for offline tests."""

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
DT_REVERSE = 1
DT_BOTH = 2
ET_BLIND = 0
ET_THROUGH_ALL = 1


def _co_init() -> None:
    if not _HAS_COM:
        raise KompasNotRunningError("pywin32/pythoncom не установлены")
    assert pythoncom is not None
    pythoncom.CoInitialize()


def _dyn(prog_id: str) -> Any:
    assert GetActiveObject is not None and Dispatch is not None
    try:
        return GetActiveObject(prog_id)
    except Exception:
        return Dispatch(prog_id)


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


def _is_legacy_part(part: Any) -> bool:
    if part is None:
        return False
    for attr in ("NewEntity", "GetDefaultEntity"):
        if not hasattr(part, attr):
            return False
    return True


def _extract_part(doc: Any, *, require_legacy_part: bool = False) -> Tuple[Optional[Any], str]:
    if doc is None:
        return None, "doc is None"
    notes: List[str] = []
    for attr in ("TopPart", "topPart", "Part"):
        try:
            v = getattr(doc, attr, None)
            if v is None:
                continue
            part = v() if callable(v) else v
            if part is not None:
                if require_legacy_part and not _is_legacy_part(part):
                    notes.append(f"{attr}: not legacy")
                    continue
                return part, attr
        except Exception as e:
            notes.append(f"{attr}:{e}")
    try:
        p = doc.GetPart(P_TOP_PART)
        if p is not None and (not require_legacy_part or _is_legacy_part(p)):
            return p, "GetPart(-1)"
    except Exception as e:
        notes.append(f"GetPart:{e}")
    for name in ("Document3D", "ActiveDocument3D"):
        try:
            inner = _as_prop_or_call(doc, name)
            if inner is not None and inner is not doc:
                p, how = _extract_part(inner, require_legacy_part=require_legacy_part)
                if p is not None:
                    return p, f"{name}->{how}"
        except Exception as e:
            notes.append(f"{name}:{e}")
    return None, "; ".join(notes) or "part not found"


class KompasApp:
    def __init__(self, k5: Any, app7: Optional[Any]):
        self.k5 = k5
        self.app7 = app7

    @classmethod
    def connect(cls) -> "KompasApp":
        _co_init()
        app7 = k5 = None
        try:
            app7 = _dyn("Kompas.Application.7")
        except Exception:
            pass
        try:
            k5 = _dyn("Kompas.Application.5")
        except Exception:
            pass
        if app7 is None and k5 is None:
            raise KompasNotRunningError("КОМПАС не запущен")
        return cls(k5, app7)

    @classmethod
    def connect_or_launch(cls, visible: bool = True) -> "KompasApp":
        return cls.connect()

    @property
    def visible(self) -> bool:
        for app in (self.app7, self.k5):
            if app is None:
                continue
            try:
                return bool(getattr(app, "Visible", True))
            except Exception:
                pass
        return True

    def hide_messages(self, hide: bool = True) -> None:
        for app in (self.app7, self.k5):
            if app is None:
                continue
            for attr in ("HideMessage", "hideMessage"):
                try:
                    setattr(app, attr, 1 if hide else 0)
                except Exception:
                    pass

    def _create_via_api7(self) -> Tuple[Optional[Any], Optional[Any], str]:
        if self.app7 is None:
            return None, None, "no app7"
        try:
            docs = self.app7.Documents
            doc = docs.Add(4, True)
            part, how = _extract_part(doc, require_legacy_part=True)
            if part is not None:
                return doc, part, f"api7:{how}"
            return doc, None, f"api7 no part:{how}"
        except Exception as e:
            return None, None, f"api7 err:{e}"

    def _create_via_api5(self) -> Tuple[Optional[Any], Optional[Any], str]:
        if self.k5 is None:
            return None, None, "no k5"
        try:
            d3 = _as_prop_or_call(self.k5, "Document3D")
            if d3 is None:
                return None, None, "no Document3D"
            part, how = _extract_part(d3, require_legacy_part=True)
            return d3, part, f"api5:{how}"
        except Exception as e:
            return None, None, f"api5 err:{e}"

    def _from_active(self) -> Tuple[Optional[Any], Optional[Any], str]:
        if self.app7 is not None:
            try:
                ad = self.app7.ActiveDocument
                part, how = _extract_part(ad, require_legacy_part=True)
                if part is not None:
                    return ad, part, f"active7:{how}"
            except Exception:
                pass
        if self.k5 is not None:
            try:
                d3 = _as_prop_or_call(self.k5, "ActiveDocument3D")
                part, how = _extract_part(d3, require_legacy_part=True)
                if part is not None:
                    return d3, part, f"active5:{how}"
            except Exception:
                pass
        return None, None, "no active"

    def new_part_document(self) -> Tuple[Any, Any]:
        doc, part, how = self._create_via_api7()
        if part is not None:
            return doc, part
        doc, part, how2 = self._create_via_api5()
        if part is not None:
            return doc, part
        raise KompasError(f"Не удалось создать деталь: {how}; {how2}")


def get_app(auto_launch: bool = True) -> KompasApp:
    if not _HAS_COM:
        raise KompasNotRunningError(
            "pywin32/pythoncom не установлены (только Windows+КОМПАС)"
        )
    if auto_launch:
        return KompasApp.connect_or_launch()
    return KompasApp.connect()
