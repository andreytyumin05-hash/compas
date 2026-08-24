"""
Подключение к КОМПАС через API5 (Kompas.Application.5) — рабочий путь для v23.

Почему API5: API7 без CastTo/makepy на многих установках даёт
«Член группы не найден» и «Property Name can not be set».
API5 Document3D + GetPart + NewEntity — классика SDK.
"""

from __future__ import annotations

import pythoncom
from typing import Any, Optional, Tuple

from .exceptions import KompasNotRunningError, KompasError

try:
    from win32com.client import Dispatch, GetActiveObject
except ImportError as e:
    raise ImportError("Установите pywin32: pip install pywin32") from e

# Константы Obj3dType / Part_Type (из SDK, стабильные числа)
P_TOP_PART = -1
O3D_PLANE_XOY = 1
O3D_PLANE_XOZ = 2
O3D_PLANE_YOZ = 3
O3D_SKETCH = 5
O3D_BASE_EXTRUSION = 24  # первая / базовая операция выдавливания
O3D_BOSS_EXTRUSION = 25
O3D_CUT_EXTRUSION = 26
O3D_BOSS_ROTATED = 27
DT_NORMAL = 0
DT_REVERSE = 1
DT_BOTH = 2
ET_BLIND = 0
ET_THROUGH_ALL = 1


class KompasApp:
    """
    kompas5 — KompasObject (Application.5)
    app7    — Application.7 (опционально, для Visible и т.п.)
    """

    def __init__(self, kompas5: Any, app7: Optional[Any] = None):
        self.k5 = kompas5
        self.app7 = app7

    @classmethod
    def connect(cls) -> "KompasApp":
        pythoncom.CoInitialize()
        k5 = None
        app7 = None
        # API5
        try:
            k5 = GetActiveObject("Kompas.Application.5")
        except Exception:
            try:
                k5 = Dispatch("Kompas.Application.5")
            except Exception as e:
                raise KompasNotRunningError(
                    "Не удалось подключить Kompas.Application.5. "
                    "Запустите КОМПАС-3D и повторите."
                ) from e
        # API7 — не обязателен
        try:
            app7 = GetActiveObject("Kompas.Application.7")
        except Exception:
            try:
                app7 = Dispatch("Kompas.Application.7")
            except Exception:
                app7 = None

        try:
            k5.Visible = True
        except Exception:
            pass
        if app7 is not None:
            try:
                app7.Visible = True
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
        try:
            self.k5.Visible = bool(value)
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
        Создать деталь.
        Возвращает (document3d, part) где part = GetPart(-1).
        """
        try:
            doc3d = self.k5.Document3D()
        except Exception as e:
            raise KompasError(f"Document3D() недоступен: {e}") from e

        # Create(hide, isPart): hide=False → видимый, isPart=True → деталь
        ok = doc3d.Create(False, True)
        if ok is False:
            # некоторые версии возвращают None вместо True
            pass

        try:
            part = doc3d.GetPart(P_TOP_PART)
        except Exception as e:
            raise KompasError(
                f"GetPart(pTop_Part) не удался: {e}. "
                "Документ мог создаться пустым — закройте его вручную."
            ) from e

        if part is None:
            raise KompasError("GetPart вернул None")

        return doc3d, part


def get_app(auto_launch: bool = True) -> KompasApp:
    return KompasApp.connect_or_launch()
