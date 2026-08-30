"""Экспорт модели, закрытие документа, временные файлы."""

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

_TMP_ROOT = Path(os.environ.get("COMPAS_TMP", Path.cwd() / ".compas_tmp"))

# расширение → предпочтительный fmt-алиас
_FMT_EXT = {
    "m3d": ".m3d",
    "a3d": ".a3d",
    "step": ".step",
    "stp": ".step",
    "stl": ".stl",
    "iges": ".iges",
    "igs": ".iges",
}


def session_dir(user_id: str = "local") -> Path:
    d = _TMP_ROOT / f"{user_id}_{uuid.uuid4().hex[:12]}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def safe_delete_path(path: Path) -> None:
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


def _ensure_extension(path: Path, fmt: str) -> Path:
    ext = _FMT_EXT.get(fmt.lower(), f".{fmt.lower()}")
    if path.suffix.lower() != ext.lower():
        return path.with_suffix(ext)
    return path


def _try_saveas(obj: Any, path: Path, errors: List[str], label: str) -> bool:
    if obj is None:
        return False
    for method in ("SaveAs", "saveAs", "SaveAsDocument"):
        try:
            fn = getattr(obj, method, None)
            if fn is None:
                continue
            if callable(fn):
                fn(str(path))
            if path.exists() and path.stat().st_size > 0:
                return True
        except Exception as e:
            errors.append(f"{label}.{method}: {e}")
    return False


# typing Any without importing in signature noise
from typing import Any  # noqa: E402


def export_part(
    part: "Part",
    path: str | Path,
    fmt: str = "m3d",
) -> Path:
    """
    Сохранить деталь.

    fmt:
      m3d  — нативный КОМПАС-деталь (по умолчанию)
      step/stp, stl, iges — обменные форматы

    Example:
        part.export("out/part.m3d", fmt="m3d")
        part.export("out/part.step", fmt="step")
    """
    fmt = fmt.lower().strip()
    if fmt == "stp":
        fmt = "step"
    path = _ensure_extension(Path(path), fmt)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            path.unlink()
        except Exception:
            pass

    errors: List[str] = []

    # 1) документ, с которым создали Part
    if _try_saveas(part._doc3d, path, errors, "doc3d"):
        return path

    # 2) API7 ActiveDocument
    try:
        if part.app.app7 is not None:
            ad = part.app.app7.ActiveDocument
            if _try_saveas(ad, path, errors, "app7.ActiveDocument"):
                return path
    except Exception as e:
        errors.append(f"app7.ActiveDocument: {e}")

    # 3) API5 ActiveDocument3D as property
    try:
        if part.app.k5 is not None:
            d3 = getattr(part.app.k5, "ActiveDocument3D", None)
            if _try_saveas(d3, path, errors, "ActiveDocument3D"):
                return path
    except Exception as e:
        errors.append(f"ActiveDocument3D: {e}")

    raise KompasOperationError(
        f"SaveAs → {path} (fmt={fmt}) не удался. "
        + "; ".join(errors[:6])
    )


def close_document(part: "Part", *, save: bool = False) -> None:
    """
    Закрыть документ детали в КОМПАС (best-effort).

    save=True — сначала Save/SaveAs во временный путь не делается здесь;
    предполагается, что export уже вызван при необходимости.
    """
    errors = []
    doc = part._doc3d

    if save:
        for method in ("Save", "save"):
            try:
                fn = getattr(doc, method, None)
                if callable(fn):
                    fn()
                    break
            except Exception as e:
                errors.append(f"Save: {e}")

    closed = False
    for obj, label in (
        (doc, "doc"),
        (
            getattr(part.app.app7, "ActiveDocument", None) if part.app.app7 else None,
            "app7",
        ),
    ):
        if obj is None:
            continue
        for method, args in (
            ("Close", (False,)),  # often Close(false) = don't save
            ("Close", ()),
            ("close", ()),
        ):
            try:
                fn = getattr(obj, method, None)
                if not callable(fn):
                    continue
                try:
                    fn(*args)
                except TypeError:
                    fn()
                closed = True
                break
            except Exception as e:
                errors.append(f"{label}.{method}: {e}")
        if closed:
            break

    # API7 Documents close active
    if not closed and part.app.app7 is not None:
        try:
            ad = part.app.app7.ActiveDocument
            if ad is not None:
                try:
                    ad.Close(False)
                    closed = True
                except Exception:
                    try:
                        ad.Close()
                        closed = True
                    except Exception as e:
                        errors.append(f"Close active: {e}")
        except Exception as e:
            errors.append(f"active close: {e}")

    if not closed and errors:
        # не падаем — бот всё равно чистит файлы
        pass


def export_and_cleanup(
    part: "Part",
    out_dir: Path,
    formats: Optional[List[str]] = None,
    *,
    close: bool = True,
) -> List[Path]:
    """
    Экспорт в несколько форматов, опционально закрыть документ.
    По умолчанию: m3d + step.
    """
    formats = formats or ["m3d", "step"]
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    paths: List[Path] = []
    errors: List[str] = []
    for fmt in formats:
        try:
            p = export_part(part, out_dir / f"part.{fmt}", fmt=fmt)
            paths.append(p)
        except Exception as e:
            errors.append(f"{fmt}: {e}")
    if close:
        try:
            close_document(part, save=False)
        except Exception as e:
            errors.append(f"close: {e}")
    if not paths:
        raise KompasOperationError("Ни один формат не сохранён: " + "; ".join(errors))
    return paths
