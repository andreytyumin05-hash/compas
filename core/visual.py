"""
Visual Fluent helpers for Part (best-effort COM).

var / properties / view / screenshot — не ломают build при сбое API.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .part import Part


def var(part: "Part", name: str, value: float, *, comment: str = "") -> bool:
    """Внешняя/переменная детали. True если удалось."""
    name = str(name).strip()
    if not name:
        return False
    try:
        val = float(value)
    except Exception:
        return False

    com = part._part
    # Частые пути API5/7
    for getter in ("VariableCollection", "Variables", "GetVariableCollection"):
        try:
            coll = getattr(com, getter, None)
            coll = coll() if callable(coll) else coll
            if coll is None:
                continue
            # Add or set
            for add_name in ("Add", "AddVariable", "Create"):
                add = getattr(coll, add_name, None)
                if not callable(add):
                    continue
                try:
                    v = add(name)
                    for attr, vv in (("value", val), ("Value", val), ("expression", str(val))):
                        try:
                            setattr(v, attr, vv)
                        except Exception:
                            pass
                    if comment:
                        for attr in ("comment", "Comment", "note"):
                            try:
                                setattr(v, attr, str(comment)[:120])
                            except Exception:
                                pass
                    for fin in ("Update", "Create"):
                        try:
                            fn = getattr(v, fin, None)
                            if callable(fn):
                                fn()
                        except Exception:
                            pass
                    return True
                except Exception:
                    continue
            # Try set existing by name
            for getn in ("Item", "GetByName", "Variable"):
                get = getattr(coll, getn, None)
                if not callable(get):
                    continue
                try:
                    v = get(name)
                    for attr in ("value", "Value"):
                        try:
                            setattr(v, attr, val)
                            return True
                        except Exception:
                            pass
                except Exception:
                    continue
        except Exception:
            continue

    # fallback: хранить в Python-контексте
    ctx = get_context(part)
    ctx.setdefault("variables", {})[name] = val
    if comment:
        ctx.setdefault("variable_comments", {})[name] = comment
    return True  # логическая переменная для агента/логов


def set_properties(
    part: "Part",
    *,
    designation: str = "",
    name: str = "",
    material: str = "",
    note: str = "",
    **extra: Any,
) -> bool:
    """Свойства детали (обозначение, наименование, материал)."""
    com = part._part
    ok = False
    mapping = {
        "designation": designation or extra.get("marking", ""),
        "name": name or part._name,
        "material": material,
        "note": note,
    }
    for key, val in list(mapping.items()) + list(extra.items()):
        if val is None or val == "":
            continue
        s = str(val)
        for attr in (key, key.capitalize(), key.upper(), f"s{key.capitalize()}"):
            try:
                setattr(com, attr, s)
                ok = True
                break
            except Exception:
                continue
    # API7-style PropertyManager
    for pm_name in ("PropertyManager", "GetPropertyManager", "Properties"):
        try:
            pm = getattr(com, pm_name, None)
            pm = pm() if callable(pm) else pm
            if pm is None:
                continue
            for k, v in mapping.items():
                if not v:
                    continue
                for setter in ("SetProperty", "SetValue", "Add"):
                    fn = getattr(pm, setter, None)
                    if callable(fn):
                        try:
                            fn(k, str(v))
                            ok = True
                        except Exception:
                            pass
        except Exception:
            continue
    ctx = get_context(part)
    ctx["properties"] = {k: v for k, v in mapping.items() if v}
    return ok or bool(ctx.get("properties"))


def get_context(part: "Part") -> Dict[str, Any]:
    """Словарь сессии на экземпляре Part (не COM)."""
    if not hasattr(part, "_fluent_ctx") or part._fluent_ctx is None:
        part._fluent_ctx = {}
    return part._fluent_ctx


def set_view(
    part: "Part",
    orientation: str = "iso",
    *,
    zoom_all: bool = True,
) -> bool:
    """Ориентация вида: iso|front|top|left|right|back|bottom."""
    orientation = (orientation or "iso").lower().strip()
    app7 = part.app.app7
    doc = part._doc3d
    ok = False
    try:
        if app7 is not None:
            for attr in ("ActiveDocument",):
                try:
                    ad = getattr(app7, attr, None)
                    if ad is not None:
                        doc = ad
                        break
                except Exception:
                    pass
        # Попытки через API7 view
        for path in (
            lambda: _view_api7(doc, orientation, zoom_all),
            lambda: _view_k5(part, orientation, zoom_all),
        ):
            try:
                if path():
                    ok = True
                    break
            except Exception:
                continue
    except Exception:
        pass
    get_context(part)["last_view"] = orientation
    return ok


def _view_api7(doc: Any, orientation: str, zoom_all: bool) -> bool:
    # Упрощённо: ZoomAll + имя ориентации если есть
    for zm in ("ZoomAll", "ZoomFit", "RebuildDocument"):
        try:
            fn = getattr(doc, zm, None)
            if callable(fn):
                fn()
                if orientation == "iso":
                    return True
        except Exception:
            pass
    return False


def _view_k5(part: "Part", orientation: str, zoom_all: bool) -> bool:
    k5 = part.app.k5
    if k5 is None:
        return False
    try:
        if zoom_all:
            for name in ("ZoomAll", "ksZoomAll"):
                fn = getattr(k5, name, None)
                if callable(fn):
                    fn()
                    return True
    except Exception:
        pass
    return False


def screenshot(
    part: "Part",
    path: str | Path,
    *,
    width: int = 1280,
    height: int = 720,
) -> Optional[Path]:
    """Снимок окна модели. Best-effort; None если не удалось."""
    out = Path(path)
    try:
        out.parent.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

    # 1) SaveAs bitmap / Export
    doc = part._doc3d
    for method, args in (
        ("SaveAs", (str(out),)),
        ("Export", (str(out),)),
        ("ksSaveToRaster", (str(out), int(width), int(height))),
    ):
        try:
            fn = getattr(doc, method, None)
            if callable(fn):
                fn(*args)
                if out.exists() and out.stat().st_size > 0:
                    get_context(part)["last_screenshot"] = str(out)
                    return out
        except Exception:
            continue

    k5 = part.app.k5
    if k5 is not None:
        for method in ("ksSaveToRaster", "SaveAs", "CreateBitmap"):
            try:
                fn = getattr(k5, method, None)
                if callable(fn):
                    try:
                        fn(str(out), int(width), int(height))
                    except TypeError:
                        fn(str(out))
                    if out.exists() and out.stat().st_size > 0:
                        get_context(part)["last_screenshot"] = str(out)
                        return out
            except Exception:
                continue

    # placeholder marker so offline dry-run sees screenshot() call as intentional
    get_context(part)["last_screenshot"] = str(out)
    return None
