"""
Безопасная работа с COM без обязательного makepy/CastTo.

Ошибка "This COM object can not automate the makepy process"
возникает, когда win32com.CastTo пытается сгенерировать обёртку.
Мы используем late binding: объект как есть.
"""

from __future__ import annotations

from typing import Any


def safe_cast(obj: Any, _interface_name: str = "") -> Any:
    """
    Раньше здесь был CastTo. Теперь просто возвращаем obj.
    Late binding через IDispatch достаточен для КОМПАС API7.
    """
    return obj


def com_get(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return default
