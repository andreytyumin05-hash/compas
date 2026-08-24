"""
Подключение к КОМПАС-3D через COM (API7).

Требования:
- Windows
- Установленный КОМПАС-3D (с поддержкой API)
- pywin32
"""

from __future__ import annotations

import pythoncom
from typing import Any, Optional

from .exceptions import KompasNotRunningError, KompasError

try:
    from win32com.client import Dispatch, GetActiveObject, gencache
except ImportError as e:
    raise ImportError(
        "pywin32 не установлен. Выполните: pip install pywin32"
    ) from e


# GUID модулей API7 (стандартные для КОМПАС)
_API7_GUID = "{69AC2981-37C0-4379-84FD-5DD2F3C0A520}"
_CONST3D_GUID = "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}"
_CONST_GUID = "{75C9F5D0-B5B8-4526-8681-9903C567D2ED}"


class KompasApp:
    """
    Обёртка над приложением КОМПАС-3D (API7).

    Использование:
        app = KompasApp.connect()          # к уже запущенному
        app = KompasApp.launch()           # запустить новый экземпляр
        app = KompasApp.connect_or_launch()
    """

    def __init__(self, application: Any, constants_3d: Any, constants: Any):
        self._app = application
        self._const3d = constants_3d
        self._const = constants

    # ------------------------------------------------------------------
    # Фабричные методы
    # ------------------------------------------------------------------

    @classmethod
    def connect(cls) -> "KompasApp":
        """Подключиться к уже запущенному КОМПАС-3D."""
        pythoncom.CoInitialize()
        try:
            raw = GetActiveObject("Kompas.Application.7")
        except Exception as e:
            raise KompasNotRunningError(
                "КОМПАС-3D не запущен. Запустите программу и повторите попытку."
            ) from e
        return cls._from_raw(raw)

    @classmethod
    def launch(cls, visible: bool = True) -> "KompasApp":
        """Запустить новый экземпляр КОМПАС-3D."""
        pythoncom.CoInitialize()
        try:
            raw = Dispatch("Kompas.Application.7")
        except Exception as e:
            raise KompasError(
                "Не удалось запустить КОМПАС-3D. Проверьте установку и регистрацию COM."
            ) from e
        app = cls._from_raw(raw)
        app.visible = visible
        return app

    @classmethod
    def connect_or_launch(cls, visible: bool = True) -> "KompasApp":
        """Сначала пробуем подключиться, иначе запускаем."""
        try:
            return cls.connect()
        except KompasNotRunningError:
            return cls.launch(visible=visible)

    @classmethod
    def _from_raw(cls, raw_app: Any) -> "KompasApp":
        try:
            api7 = gencache.EnsureModule(_API7_GUID, 0, 1, 0)
            const3d = gencache.EnsureModule(_CONST3D_GUID, 0, 1, 0).constants
            const = gencache.EnsureModule(_CONST_GUID, 0, 1, 0).constants

            # Получаем типизированный IApplication
            application = api7.IApplication(
                raw_app._oleobj_.QueryInterface(
                    api7.IApplication.CLSID, pythoncom.IID_IDispatch
                )
            )
            return cls(application, const3d, const)
        except Exception as e:
            raise KompasError(
                f"Ошибка инициализации API7: {e}. "
                "Убедитесь, что установлена версия КОМПАС с SDK/API."
            ) from e

    # ------------------------------------------------------------------
    # Свойства
    # ------------------------------------------------------------------

    @property
    def raw(self) -> Any:
        """Сырой COM-объект IApplication."""
        return self._app

    @property
    def const3d(self) -> Any:
        """Константы 3D API."""
        return self._const3d

    @property
    def const(self) -> Any:
        """Общие константы API."""
        return self._const

    @property
    def visible(self) -> bool:
        return bool(self._app.Visible)

    @visible.setter
    def visible(self, value: bool) -> None:
        self._app.Visible = bool(value)

    @property
    def active_document(self) -> Any:
        return self._app.ActiveDocument

    # ------------------------------------------------------------------
    # Документы
    # ------------------------------------------------------------------

    def new_part(self, name: str = "Деталь") -> Any:
        """
        Создать новый документ детали (ksDocumentPart = 4).
        Возвращает IKompasDocument3D.
        """
        # 4 = ksDocumentPart
        doc = self._app.Documents.Add(4, True)
        if doc is None:
            raise KompasError("Не удалось создать документ детали")

        # Приводим к IKompasDocument3D
        from win32com.client import CastTo
        doc3d = CastTo(self._app.ActiveDocument, "IKompasDocument3D")
        part = doc3d.TopPart
        if name:
            part.Name = name
            part.Update()
        return doc3d

    def hide_messages(self, hide: bool = True) -> None:
        """Скрывать/показывать системные сообщения КОМПАС."""
        # ksHideMessageYes / ksHideMessageNo
        try:
            self._app.HideMessage = (
                self._const.ksHideMessageYes if hide else self._const.ksHideMessageNo
            )
        except Exception:
            pass  # не критично


def get_app(auto_launch: bool = True) -> KompasApp:
    """
    Удобная функция: получить приложение КОМПАС.

    auto_launch=True  — подключиться или запустить
    auto_launch=False — только подключиться (иначе ошибка)
    """
    if auto_launch:
        return KompasApp.connect_or_launch()
    return KompasApp.connect()
