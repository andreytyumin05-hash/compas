"""
Подключение к КОМПАС-3D через COM (API7).

Требования:
- Windows
- Установленный КОМПАС-3D (с поддержкой API)
- pywin32
"""

from __future__ import annotations

import pythoncom
from typing import Any

from .exceptions import KompasNotRunningError, KompasError

try:
    from win32com.client import Dispatch, GetActiveObject, gencache, CastTo
except ImportError as e:
    raise ImportError(
        "pywin32 не установлен. В активированном venv выполните:\n"
        "  pip install pywin32"
    ) from e


# GUID модулей API7 (стандартные для КОМПАС)
_API7_GUID = "{69AC2981-37C0-4379-84FD-5DD2F3C0A520}"
_CONST3D_GUID = "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}"
_CONST_GUID = "{75C9F5D0-B5B8-4526-8681-9903C567D2ED}"


class _LazyConstants:
    """
    Запасной вариант констант, если gencache не сработал.
    Числовые значения соответствуют типичным константам КОМПАС API.
    """

    # Плоскости
    o3d_planeXOY = 1
    o3d_planeXOZ = 2
    o3d_planeYOZ = 3

    # Операции
    o3d_bossExtrusion = 25
    o3d_cutExtrusion = 26
    o3d_bossRotated = 27

    # Направление
    dtNormal = 0
    dtReverse = 1
    dtBoth = 2

    # Тип окончания
    etBlind = 0
    etThroughAll = 1

    # Сообщения
    ksHideMessageNo = 0
    ksHideMessageYes = 1


class KompasApp:
    """
    Обёртка над приложением КОМПАС-3D (API7).

    Использование:
        app = KompasApp.connect()           # к уже запущенному
        app = KompasApp.launch()            # запустить новый
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
                "КОМПАС-3D не запущен или COM не отвечает.\n"
                "1) Запустите КОМПАС-3D\n"
                "2) Повторите команду"
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
                "Не удалось запустить КОМПАС-3D через COM.\n"
                "Проверьте, что программа установлена и COM-сервер зарегистрирован."
            ) from e
        app = cls._from_raw(raw)
        app.visible = visible
        return app

    @classmethod
    def connect_or_launch(cls, visible: bool = True) -> "KompasApp":
        try:
            return cls.connect()
        except KompasNotRunningError:
            return cls.launch(visible=visible)

    @classmethod
    def _from_raw(cls, raw_app: Any) -> "KompasApp":
        """
        Инициализация API7.
        Сначала пробуем gencache (типизированные интерфейсы),
        при ошибке — late binding + запасные константы.
        """
        const3d: Any = _LazyConstants()
        const: Any = _LazyConstants()
        application: Any = raw_app

        try:
            api7 = gencache.EnsureModule(_API7_GUID, 0, 1, 0)
            const3d_mod = gencache.EnsureModule(_CONST3D_GUID, 0, 1, 0)
            const_mod = gencache.EnsureModule(_CONST_GUID, 0, 1, 0)
            const3d = const3d_mod.constants
            const = const_mod.constants
            application = api7.IApplication(
                raw_app._oleobj_.QueryInterface(
                    api7.IApplication.CLSID, pythoncom.IID_IDispatch
                )
            )
        except Exception:
            # Late binding — тоже рабочий режим
            application = raw_app

        return cls(application, const3d, const)

    # ------------------------------------------------------------------
    # Свойства
    # ------------------------------------------------------------------

    @property
    def raw(self) -> Any:
        return self._app

    @property
    def const3d(self) -> Any:
        return self._const3d

    @property
    def const(self) -> Any:
        return self._const

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

    # ------------------------------------------------------------------
    # Документы
    # ------------------------------------------------------------------

    def new_part(self, name: str = "Деталь") -> Any:
        """
        Создать новый документ детали (тип 4 = ksDocumentPart).
        Возвращает объект документа 3D.
        """
        doc = self._app.Documents.Add(4, True)
        if doc is None:
            raise KompasError("Не удалось создать документ детали")

        try:
            doc3d = CastTo(self._app.ActiveDocument, "IKompasDocument3D")
        except Exception:
            doc3d = self._app.ActiveDocument

        try:
            part = doc3d.TopPart
            if name:
                part.Name = name
                part.Update()
        except Exception:
            pass

        return doc3d

    def hide_messages(self, hide: bool = True) -> None:
        try:
            val = (
                getattr(self._const, "ksHideMessageYes", 1)
                if hide
                else getattr(self._const, "ksHideMessageNo", 0)
            )
            self._app.HideMessage = val
        except Exception:
            pass


def get_app(auto_launch: bool = True) -> KompasApp:
    """
    Получить приложение КОМПАС.

    auto_launch=True  — подключиться или запустить
    auto_launch=False — только к уже запущенному
    """
    if auto_launch:
        return KompasApp.connect_or_launch()
    return KompasApp.connect()
