"""
Подключение к КОМПАС-3D через COM.

ВАЖНО (по diagnose от 2026-08-25):
- GetActiveObject('Kompas.Application.5') и .7 — OK
- У App5 есть Document3D, у App7 есть Documents
- Вызов Document3D() / Documents.Add() давал DISP_E_MEMBERNOTFOUND
  (-2147352573), часто из-за битого gencache/EnsureModule/QueryInterface

Стратегия:
- ТОЛЬКО win32com.client.dynamic.Dispatch (late binding, без makepy)
- Не использовать gencache.EnsureModule / QueryInterface для Application
- Документ: сначала API7 Documents.Add / AddWithDefaultSettings
- Деталь: API5 ActiveDocument3D().GetPart(-1) или Document3D().Create
- Fallback: пользователь вручную создаёт деталь → from_active()
"""

from __future__ import annotations

import pythoncom
from typing import Any, Optional, Tuple, List

from .exceptions import KompasNotRunningError, KompasError

try:
    from win32com.client import GetActiveObject
    from win32com.client.dynamic import Dispatch as DynDispatch
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


def _co_init() -> None:
    try:
        pythoncom.CoInitialize()
    except Exception:
        pass


def _dyn(prog_id: str) -> Any:
    """Динамический COM-объект (без typelib cache)."""
    _co_init()
    try:
        raw = GetActiveObject(prog_id)
    except Exception:
        raw = DynDispatch(prog_id)
    # Оборачиваем в dynamic, даже если пришли из GetActiveObject
    try:
        return DynDispatch(raw)
    except Exception:
        return raw


def _try_call(obj: Any, names: List[str], *args) -> Tuple[bool, Any, str]:
    """Пробует вызвать первый существующий метод из списка имён."""
    errors = []
    for name in names:
        try:
            fn = getattr(obj, name)
        except Exception as e:
            errors.append(f"{name} getattr: {e}")
            continue
        try:
            if args:
                return True, fn(*args), name
            # без аргументов — и property, и method()
            try:
                return True, fn(), name + "()"
            except TypeError:
                return True, fn, name
            except Exception as e:
                errors.append(f"{name}(): {e}")
                try:
                    return True, fn, name + "(prop)"
                except Exception as e2:
                    errors.append(f"{name} prop: {e2}")
        except Exception as e:
            errors.append(f"{name} call: {e}")
    return False, None, "; ".join(errors)


class KompasApp:
    def __init__(self, k5: Any, app7: Optional[Any]):
        self.k5 = k5
        self.app7 = app7

    @classmethod
    def connect(cls) -> "KompasApp":
        k5 = None
        app7 = None
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
                f"КОМПАС COM недоступен. App5={err5}; App7={err7}. "
                "Запустите КОМПАС-3D."
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

    def _part_from_doc3d(self, doc3d: Any) -> Optional[Any]:
        if doc3d is None:
            return None
        for args in ((P_TOP_PART,), (-1,), (0,)):
            try:
                part = doc3d.GetPart(*args)
                if part is not None:
                    return part
            except Exception:
                continue
        return None

    def _create_via_api5(self) -> Tuple[Optional[Any], Optional[Any], str]:
        if self.k5 is None:
            return None, None, "k5 is None"
        notes = []

        # Document3D() как метод
        try:
            doc3d = self.k5.Document3D()
            notes.append("Document3D() ok")
            try:
                doc3d.Create(False, True)
                notes.append("Create(False,True) ok")
            except Exception as e:
                notes.append(f"Create: {e}")
            part = self._part_from_doc3d(doc3d)
            if part is not None:
                return doc3d, part, "; ".join(notes)
            notes.append("GetPart None after Create")
        except Exception as e:
            notes.append(f"Document3D(): {e}")

        # Иногда Document3D — уже объект
        try:
            doc3d = self.k5.Document3D
            if doc3d is not None and not callable(doc3d):
                notes.append("Document3D as property")
                try:
                    doc3d.Create(False, True)
                except Exception as e:
                    notes.append(f"Create on prop: {e}")
                part = self._part_from_doc3d(doc3d)
                if part is not None:
                    return doc3d, part, "; ".join(notes)
        except Exception as e:
            notes.append(f"Document3D prop: {e}")

        return None, None, "; ".join(notes)

    def _create_via_api7(self) -> Tuple[Optional[Any], Optional[Any], str]:
        if self.app7 is None:
            return None, None, "app7 is None"
        notes = []

        try:
            docs = self.app7.Documents
            notes.append(f"Documents type={type(docs)}")
        except Exception as e:
            return None, None, f"Documents: {e}"

        if docs is None:
            return None, None, "Documents is None"

        # Разные способы создать деталь
        create_attempts = [
            ("AddWithDefaultSettings(1, True)", lambda: docs.AddWithDefaultSettings(1, True)),
            ("AddWithDefaultSettings(4, True)", lambda: docs.AddWithDefaultSettings(4, True)),
            ("Add(4, True)", lambda: docs.Add(4, True)),
            ("Add(1, True)", lambda: docs.Add(1, True)),
            ("Add(5, True)", lambda: docs.Add(5, True)),
        ]

        for label, fn in create_attempts:
            try:
                fn()
                notes.append(f"{label} ok")
                break
            except Exception as e:
                notes.append(f"{label}: {e}")
        else:
            return None, None, "; ".join(notes)

        # Получить part через API5
        if self.k5 is not None:
            try:
                doc3d = self.k5.ActiveDocument3D()
                notes.append(f"ActiveDocument3D={doc3d}")
                part = self._part_from_doc3d(doc3d)
                if part is not None:
                    return doc3d, part, "; ".join(notes)
            except Exception as e:
                notes.append(f"ActiveDocument3D: {e}")

        # Через API7 ActiveDocument + иногда TopPart
        try:
            ad = self.app7.ActiveDocument
            notes.append(f"ActiveDocument={ad}")
            if ad is not None:
                for attr in ("TopPart", "topPart"):
                    try:
                        part = getattr(ad, attr)
                        if part is not None:
                            return ad, part, "; ".join(notes + [attr])
                    except Exception as e:
                        notes.append(f"{attr}: {e}")
        except Exception as e:
            notes.append(f"ActiveDocument: {e}")

        return None, None, "; ".join(notes)

    def _from_active(self) -> Tuple[Optional[Any], Optional[Any], str]:
        notes = []
        if self.k5 is not None:
            try:
                doc3d = self.k5.ActiveDocument3D()
                part = self._part_from_doc3d(doc3d)
                if part is not None:
                    return doc3d, part, "active API5"
                notes.append(f"ActiveDocument3D={doc3d}, GetPart None")
            except Exception as e:
                notes.append(f"API5 active: {e}")
        if self.app7 is not None:
            try:
                ad = self.app7.ActiveDocument
                if ad is not None:
                    try:
                        part = ad.TopPart
                        if part is not None:
                            return ad, part, "active API7 TopPart"
                    except Exception as e:
                        notes.append(f"TopPart: {e}")
            except Exception as e:
                notes.append(f"API7 active: {e}")
        return None, None, "; ".join(notes)

    def new_part_document(self) -> Tuple[Any, Any]:
        errors: List[str] = []

        doc3d, part, note = self._create_via_api7()
        if part is not None:
            return doc3d, part
        errors.append(f"API7: {note}")

        doc3d, part, note = self._create_via_api5()
        if part is not None:
            return doc3d, part
        errors.append(f"API5: {note}")

        doc3d, part, note = self._from_active()
        if part is not None:
            return doc3d, part
        errors.append(f"Active: {note}")

        raise KompasError(
            "Не удалось создать/получить деталь.\n"
            + "\n".join(f"  • {e}" for e in errors)
            + "\n\nWORKAROUND: В КОМПАСе вручную Файл→Создать→Деталь, затем:\n"
            "  python -c \"from core import Part; p=Part.from_active(); "
            "print('OK', p)\"\n"
            "Если from_active работает — можно строить в уже открытой детали."
        )


def get_app(auto_launch: bool = True) -> KompasApp:
    return KompasApp.connect()
