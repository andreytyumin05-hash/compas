"""Экспорт модели и безопасная работа с временными файлами."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

_TMP_ROOT = Path(os.environ.get("COMPAS_TMP", Path.cwd() / ".compas_tmp"))


def session_dir(user_id: str = "local") -> Path:
    """Уникальная папка сессии: user_id + uuid."""
    d = _TMP_ROOT / f"{user_id}_{uuid.uuid4().hex[:12]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_delete_path(path: Path) -> None:
    """Удалить файл или дерево; ошибки глотаем после попытки."""
    try:
        if path.is_file():
            path.unlink(missing_ok=True)
        elif path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
    except Exception:
        try:
            if path.exists():
                path.unlink(missing_ok=True)
        except Exception:
            pass


def export_part(
    part: "Part",
    path: str | Path,
    fmt: str = "step",
) -> Path:
    """
    Сохранить деталь в файл.

    fmt: step | stp | stl | iges | sat (что поддержит установка КОМПАС)

    Example:
        path = export_part(part, "out/part.step", fmt="step")
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fmt = fmt.lower().strip()
    if fmt == "stp":
        fmt = "step"

    # 1) SaveAs на документе
    doc = part._doc3d
    errors = []
    for method in ("SaveAs", "saveAs", "SaveAsDocument"):
        try:
            fn = getattr(doc, method, None)
            if fn is None:
                continue
            if callable(fn):
                fn(str(path))
            else:
                # property-style already invoked
                pass
            if path.exists() and path.stat().st_size > 0:
                return path
        except Exception as e:
            errors.append(f"{method}: {e}")

    # 2) API7 ActiveDocument SaveAs
    try:
        app = part.app
        if app.app7 is not None:
            ad = app.app7.ActiveDocument
            for method in ("SaveAs", "saveAs"):
                try:
                    getattr(ad, method)(str(path))
                    if path.exists() and path.stat().st_size > 0:
                        return path
                except Exception as e:
                    errors.append(f"app7.{method}: {e}")
    except Exception as e:
        errors.append(f"app7 path: {e}")

    raise KompasOperationError(
        f"Не удалось экспортировать в {path} (fmt={fmt}). "
        f"Проверьте, что КОМПАС умеет SaveAs в этот формат. Детали: {'; '.join(errors[:5])}"
    )
