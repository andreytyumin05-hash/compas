"""
Подключение к КОМПАС-3D.

Рабочая схема (как в макросах АСКОН):
1) Kompas.Application.5 → QueryInterface → KompasObject (API5)
2) Документ: API7 Documents.Add(ksDocumentPart) ИЛИ API5 Document3D().Create
3) Деталь: API5 ActiveDocument3D().GetPart(-1) / Document3D.GetPart(-1)
"""

from __future__ import annotations

import pythoncom
from typing import Any, Optional, Tuple

from .exceptions import KompasNotRunningError, KompasError

try:
    from win32com.client import Dispatch, GetActiveObject, gencache
except ImportError as e:
    raise ImportError("Установите pywin32: pip install pywin32") from e

# GUID typelib API5 (KompasObject)
_API5_GUID = "{0422828C-F174-495E-AC5D-D31014DBBE87}"

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

# ksDocumentPart в API7 чаще всего = 1 или 4 — пробуем оба
_DOC_PART_CANDIDATES = (1, 4, 5)


def _co_init() -> None:
    try:
        pythoncom.CoInitialize()
    except Exception:
        pass


def _dispatch_prog(prog_id: str) -> Any:
    """GetActiveObject или Dispatch."""
    try:
        return GetActiveObject(prog_id)
    except Exception:
        return Dispatch(prog_id)


def _get_kompas_object() -> Any:
    """
    Настоящий KompasObject (API5), не «голый» Application.
    Без QueryInterface метод Document3D() часто даёт «Член группы не найден».
    """
    _co_init()
    raw = None
    last_err: Exception | None = None

    for prog in ("Kompas.Application.5", "KOMPAS.Application.5"):
        try:
            raw = _dispatch_prog(prog)
            break
        except Exception as e:
            last_err = e

    if raw is None:
        raise KompasNotRunningError(
            f"Не удалось открыть Kompas.Application.5: {last_err}\n"
            "Запустите КОМПАС-3D и повторите."
        )

    # Попытка типизировать через typelib
    try:
        api5 = gencache.EnsureModule(_API5_GUID, 0, 1, 0)
        kompas = api5.KompasObject(
            raw._oleobj_.QueryInterface(api5.KompasObject.CLSID, pythoncom.IID_IDispatch)
        )
        return kompas
    except Exception:
        pass

    # Late binding: иногда Document3D уже есть на raw
    if hasattr(raw, "Document3D") or _has_com_method(raw, "Document3D"):
        return raw

    # Ещё один путь — Dispatch без GetActiveObject
    try:
        raw2 = Dispatch("Kompas.Application.5")
        try:
            api5 = gencache.EnsureModule(_API5_GUID, 0, 1, 0)
            return api5.KompasObject(
                raw2._oleobj_.QueryInterface(
                    api5.KompasObject.CLSID, pythoncom.IID_IDispatch
                )
            )
        except Exception:
            return raw2
    except Exception as e:
        raise KompasError(
            f"Не удалось получить KompasObject: {e}. "
            f"Исходный объект type={type(raw)}"
        ) from e


def _has_com_method(obj: Any, name: str) -> bool:
    try:
        getattr(obj, name)
        return True
    except Exception:
        return False


def _get_app7() -> Optional[Any]:
    for prog in ("Kompas.Application.7", "KOMPAS.Application.7"):
        try:
            return _dispatch_prog(prog)
        except Exception:
            continue
    try:
        return Dispatch("Kompas.Application.7")
    except Exception:
        return None


class KompasApp:
    def __init__(self, k5: Any, app7: Optional[Any] = None):
        self.k5 = k5
        self.app7 = app7

    @classmethod
    def connect(cls) -> "KompasApp":
        k5 = _get_kompas_object()
        app7 = _get_app7()
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
        try:
            return bool(self.k5.Visible)
        except Exception:
            return False

    @visible.setter
    def visible(self, value: bool) -> None:
        for obj in (self.k5, self.app7):
            if obj is None:
                continue
            try:
                obj.Visible = bool(value)
            except Exception:
                pass

    def hide_messages(self, hide: bool = True) -> None:
        for obj in (self.k5, self.app7):
            if obj is None:
                continue
            try:
                obj.HideMessage = 1 if hide else 0
            except Exception:
                pass

    def new_part_document(self) -> Tuple[Any, Any]:
        """
        Создать деталь, вернуть (doc3d_api5, part).
        Стратегия:
          A) API5 Document3D().Create(False, True)
          B) API7 Documents.Add(part) + API5 ActiveDocument3D()
        """
        errors: list[str] = []

        # --- A: чистый API5 ---
        try:
            doc3d = self.k5.Document3D()
            doc3d.Create(False, True)
            part = doc3d.GetPart(P_TOP_PART)
            if part is not None:
                return doc3d, part
            errors.append("API5: GetPart вернул None")
        except Exception as e:
            errors.append(f"API5 Document3D: {e}")

        # --- B: документ через API7, part через API5 ---
        if self.app7 is not None:
            for doc_type in _DOC_PART_CANDIDATES:
                try:
                    self.app7.Documents.Add(doc_type, True)
                    doc3d = self.k5.ActiveDocument3D()
                    if doc3d is None:
                        errors.append(f"API7 Add({doc_type}): ActiveDocument3D is None")
                        continue
                    part = doc3d.GetPart(P_TOP_PART)
                    if part is not None:
                        return doc3d, part
                    errors.append(f"API7 Add({doc_type}): GetPart None")
                except Exception as e:
                    errors.append(f"API7 Add({doc_type}): {e}")

        # --- C: только ActiveDocument3D, если пользователь уже создал деталь ---
        try:
            doc3d = self.k5.ActiveDocument3D()
            if doc3d is not None:
                part = doc3d.GetPart(P_TOP_PART)
                if part is not None:
                    return doc3d, part
        except Exception as e:
            errors.append(f"ActiveDocument3D: {e}")

        raise KompasError(
            "Не удалось создать/получить деталь.\n"
            + "\n".join(f"  • {e}" for e in errors)
            + "\n\nПроверьте: КОМПАС-3D запущен, есть лицензия, API/SDK не отключены."
        )


def get_app(auto_launch: bool = True) -> KompasApp:
    return KompasApp.connect_or_launch()
