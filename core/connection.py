"""
Подключение к КОМПАС-3D (runtime facts 2026-08-25 diagnose):

PROVEN:
- Python 3.14 x64, pywin32 OK
- GetActiveObject App5 + App7 OK
- app7.Documents.Add(4, True) OK  ← document creation WORKS
- gencache EnsureModule FAIL: "Библиотека не зарегистрирована" (no typelib)
- App5.Document3D() CALL → DISP_E_MEMBERNOTFOUND
- App5.ActiveDocument3D as getattr returns CDispatch, but () call → MEMBERNOTFOUND
  → treat ActiveDocument3D / Document3D as PROPERTY, not method

Strategy:
1) Create part with app7.Documents.Add(4, True) and keep the RETURNED document
2) Extract ksPart from that document (TopPart / GetPart / etc.)
3) Never rely on gencache on this machine
"""

from __future__ import annotations

import pythoncom
from typing import Any, Optional, Tuple, List

from .exceptions import KompasNotRunningError, KompasError

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
O3D_BOSS_ROTATED = 27
DT_NORMAL = 0
DT_REVERSE = 1
DT_BOTH = 2
ET_BLIND = 0
ET_THROUGH_ALL = 1

# ksDocumentPart — на этой установке Add(4, True) уже подтверждён diagnose
KS_DOCUMENT_PART = 4


def _co_init() -> None:
    try:
        pythoncom.CoInitialize()
    except Exception:
        pass


def _dyn(prog_id: str) -> Any:
    """Return the native late-bound COM wrapper.

    ``GetActiveObject`` already returns a ``win32com.client.CDispatch``.
    Re-wrapping it with ``dynamic.Dispatch`` changes nested property values
    into dynamic callable proxies on installations without a registered
    KOMPAS typelib.  In particular, that made a valid ``ActiveDocument3D``
    look like a method and led to ``DISP_E_MEMBERNOTFOUND``.  Keep the
    original wrapper all the way from ``Documents.Add`` to part extraction.
    """
    _co_init()
    try:
        return GetActiveObject(prog_id)
    except Exception:
        # Preserve the historic auto-launch behaviour for ``Part.create``.
        return Dispatch(prog_id)


def _as_prop_or_call(obj: Any, name: str) -> Any:
    """
    Return a document member strictly as a property.

    KOMPAS exposes ``ActiveDocument3D`` and ``Document3D`` as dispatch
    properties here.  A dynamic dispatch object can be callable too, so
    checking ``callable(value)`` and then invoking it is not safe.
    """
    try:
        val = getattr(obj, name)
    except Exception as e:
        raise AttributeError(f"{name}: {e}") from e

    return val


def _is_legacy_part(part: Any) -> bool:
    """Whether *part* is the API5 ``ksPart`` used by the modelling wrapper.

    API7's ``TopPart`` is an ``IPart7``.  It is a perfectly valid component,
    but it does not expose API5's ``NewEntity`` method used by ``Sketch`` and
    ``operations``.  Accessing the member is non-mutating and lets us keep
    searching for ``ksPart`` instead of returning an object that will fail
    only later at the first sketch.
    """
    try:
        return callable(getattr(part, "NewEntity"))
    except Exception:
        return False


def _extract_part(doc: Any, *, require_legacy_part: bool = False) -> Tuple[Optional[Any], str]:
    """Try every known way to get a part from a document COM object."""
    if doc is None:
        return None, "doc is None"
    notes: List[str] = []

    # Direct attributes
    for attr in ("TopPart", "topPart", "Part", "part"):
        try:
            p = getattr(doc, attr)
            if p is not None:
                if not require_legacy_part or _is_legacy_part(p):
                    return p, f"doc.{attr}"
                notes.append(f"{attr}=API7 part (no NewEntity)")
                continue
            notes.append(f"{attr}=None")
        except Exception as e:
            notes.append(f"{attr}:{e}")

    # API7 documents expose the same read-only property through this
    # Automation getter.  It matters when ``TopPart`` is not described by
    # the base document dispatch returned from Documents.Add.
    for method in ("GetTopPart", "get_TopPart"):
        try:
            p = getattr(doc, method)()
            if p is not None:
                if not require_legacy_part or _is_legacy_part(p):
                    return p, f"{method}()"
                notes.append(f"{method}()=API7 part (no NewEntity)")
                continue
            notes.append(f"{method}()=None")
        except Exception as e:
            notes.append(f"{method}():{e}")

    # GetPart(-1) API5 style
    for args in ((-1,), (P_TOP_PART,), (0,)):
        try:
            p = doc.GetPart(*args)
            if p is not None:
                if not require_legacy_part or _is_legacy_part(p):
                    return p, f"GetPart{args}"
                notes.append(f"GetPart{args}=API7 part (no NewEntity)")
                continue
            notes.append(f"GetPart{args}=None")
        except Exception as e:
            notes.append(f"GetPart{args}:{e}")

    # Nested Document3D on same object
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
            app7 = _dyn("Kompas.Application.7")
        except Exception as e:
            err7 = e
        if k5 is None and app7 is None:
            raise KompasNotRunningError(
                f"КОМПАС COM недоступен. App5={err5}; App7={err7}"
            )
        for obj in (k5, app7):
            if obj is None:
                continue
            try:
                obj.Visible = True
            except Exception:
                pass
        return cls(k5, app7)

    @classmethod
    def connect_or_launch(cls, visible: bool = True) -> "KompasApp":
        return cls.connect()

    @property
    def visible(self) -> bool:
        for obj in (self.k5, self.app7):
            if obj is None:
                continue
            try:
                return bool(obj.Visible)
            except Exception:
                continue
        return False

    def hide_messages(self, hide: bool = True) -> None:
        for obj in (self.k5, self.app7):
            if obj is None:
                continue
            try:
                obj.HideMessage = 1 if hide else 0
            except Exception:
                pass

    def _create_via_api7(self) -> Tuple[Optional[Any], Optional[Any], str]:
        if self.app7 is None:
            return None, None, "app7 is None"
        notes: List[str] = []

        try:
            docs = self.app7.Documents
        except Exception as e:
            return None, None, f"Documents: {e}"

        doc = None
        # Order: proven Add(4,True) first from diagnose
        for label, fn in [
            ("Add(4,True)", lambda: docs.Add(4, True)),
            ("AddWithDefaultSettings(1,True)", lambda: docs.AddWithDefaultSettings(1, True)),
            ("Add(1,True)", lambda: docs.Add(1, True)),
        ]:
            try:
                doc = fn()
                notes.append(f"{label} OK type={type(doc)}")
                break
            except Exception as e:
                notes.append(f"{label}: {e}")

        if doc is None:
            # last opened item
            try:
                n = int(docs.Count)
                doc = docs.Item(n)
                notes.append(f"fallback Item({n})")
            except Exception as e:
                notes.append(f"Item fallback: {e}")
                return None, None, "; ".join(notes)

        # ``Documents.Add`` returns an API7 IKompasDocument.  Probe it first,
        # but only accept an API5 ksPart because the rest of core uses
        # ``NewEntity``.  Its TopPart is IPart7 and is not interchangeable.
        part, how = _extract_part(doc, require_legacy_part=True)
        if part is not None:
            return doc, part, "; ".join(notes + [how])

        # ActiveDocument after Add
        try:
            ad = self.app7.ActiveDocument
            notes.append("try ActiveDocument")
            part, how = _extract_part(ad, require_legacy_part=True)
            if part is not None:
                return ad, part, "; ".join(notes + [how])
            notes.append(f"ActiveDocument extract: {how}")
        except Exception as e:
            notes.append(f"ActiveDocument: {e}")

        # API5 property ActiveDocument3D (NOT call)
        if self.k5 is not None:
            try:
                d3 = _as_prop_or_call(self.k5, "ActiveDocument3D")
                notes.append(f"ActiveDocument3D prop type={type(d3)}")
                part, how = _extract_part(d3, require_legacy_part=True)
                if part is not None:
                    return d3, part, "; ".join(notes + [how])
                notes.append(f"extract from ActiveDocument3D: {how}")
            except Exception as e:
                notes.append(f"ActiveDocument3D: {e}")

        return None, None, "; ".join(notes)

    def _create_via_api5(self) -> Tuple[Optional[Any], Optional[Any], str]:
        if self.k5 is None:
            return None, None, "k5 is None"
        notes: List[str] = []

        # Prefer property access
        try:
            doc3d = _as_prop_or_call(self.k5, "Document3D")
            notes.append(f"Document3D access type={type(doc3d)}")
            try:
                doc3d.Create(False, True)
                notes.append("Create OK")
            except Exception as e:
                notes.append(f"Create: {e}")
            part, how = _extract_part(doc3d, require_legacy_part=True)
            if part is not None:
                return doc3d, part, "; ".join(notes + [how])
            notes.append(f"extract: {how}")
        except Exception as e:
            notes.append(f"Document3D path: {e}")

        return None, None, "; ".join(notes)

    def _from_active(self) -> Tuple[Optional[Any], Optional[Any], str]:
        notes: List[str] = []

        if self.app7 is not None:
            try:
                ad = self.app7.ActiveDocument
                part, how = _extract_part(ad, require_legacy_part=True)
                if part is not None:
                    return ad, part, f"app7.ActiveDocument->{how}"
                notes.append(f"app7.ActiveDocument: {how}")
            except Exception as e:
                notes.append(f"app7.ActiveDocument: {e}")

        if self.k5 is not None:
            try:
                d3 = _as_prop_or_call(self.k5, "ActiveDocument3D")
                part, how = _extract_part(d3, require_legacy_part=True)
                if part is not None:
                    return d3, part, f"ActiveDocument3D->{how}"
                notes.append(f"ActiveDocument3D: {how}")
            except Exception as e:
                notes.append(f"ActiveDocument3D: {e}")

        return None, None, "; ".join(notes)

    def new_part_document(self) -> Tuple[Any, Any]:
        errors: List[str] = []

        doc, part, note = self._create_via_api7()
        if part is not None:
            return doc, part
        errors.append(f"API7: {note}")

        doc, part, note = self._create_via_api5()
        if part is not None:
            return doc, part
        errors.append(f"API5: {note}")

        doc, part, note = self._from_active()
        if part is not None:
            return doc, part
        errors.append(f"Active: {note}")

        raise KompasError(
            "Документ возможно создан (Add OK), но Part не извлечён.\n"
            + "\n".join(f"  • {e}" for e in errors)
            + "\n\nTypelib не зарегистрирована (gencache FAIL) — нужен part с документа Add."
        )


def get_app(auto_launch: bool = True) -> KompasApp:
    return KompasApp.connect()
