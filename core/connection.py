"""
Подключение к КОМПАС-3D через COM.
"""

from __future__ import annotations

import pythoncom
from typing import Any

from .exceptions import KompasNotRunningError, KompasError
from .constants_resolve import CONST3D

try:
    from win32com.client import Dispatch, GetActiveObject
except ImportError as e:
    raise ImportError(
        "pywin32 не установлен. В venv: pip install pywin32"
    ) from e


class KompasApp:
    def __init__(self, application: Any):
        self._app = application
        self._const3d = CONST3D

    @classmethod
    def connect(cls) -> "KompasApp":
        pythoncom.CoInitialize()
        try:
            raw = GetActiveObject("Kompas.Application.7")
        except Exception as e:
            raise KompasNotRunningError(
                "КОМПАС-3D не запущен. Откройте КОМПАС и повторите."
            ) from e
        return cls(raw)

    @classmethod
    def launch(cls, visible: bool = True) -> "KompasApp":
        pythoncom.CoInitialize()
        try:
            raw = Dispatch("Kompas.Application.7")
        except Exception as e:
            raise KompasError("Не удалось запустить КОМПАС-3D через COM.") from e
        app = cls(raw)
        app.visible = visible
        return app

    @classmethod
    def connect_or_launch(cls, visible: bool = True) -> "KompasApp":
        try:
            return cls.connect()
        except KompasNotRunningError:
            return cls.launch(visible=visible)

    @property
    def raw(self) -> Any:
        return self._app

    @property
    def const3d(self) -> Any:
        return self._const3d

    @property
    def visible(self) -> bool:
        try:
            return bool(self._app.Visible)
        except Exception:
            return False

    @visible.setter
    def visible(self, value: bool) -> None:
        try:
            self._app.Visible = bool(value)
        except Exception:
            pass

    @property
    def active_document(self) -> Any:
        try:
            return self._app.ActiveDocument
        except Exception:
            return None

    def new_part(self, name: str = "Деталь") -> Any:
        """
        Создать деталь.
        Documents.Add(4, True) — ksDocumentPart.
        """
        docs = self._app.Documents
        doc = docs.Add(4, True)
        if doc is None:
            raise KompasError("Documents.Add вернул None")

        # ActiveDocument после Add
        doc3d = self._app.ActiveDocument
        try:
            part = doc3d.TopPart
            if name:
                part.Name = str(name)
                try:
                    part.Update()
                except Exception:
                    pass
        except Exception as e:
            raise KompasError(f"Документ создан, но TopPart недоступен: {e}") from e

        return doc3d

    def hide_messages(self, hide: bool = True) -> None:
        try:
            # 1 = hide yes (часто), 0 = no
            self._app.HideMessage = 1 if hide else 0
        except Exception:
            pass


def get_app(auto_launch: bool = True) -> KompasApp:
    if auto_launch:
        return KompasApp.connect_or_launch()
    return KompasApp.connect()
