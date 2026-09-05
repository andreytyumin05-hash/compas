"""API5 размеры эскиза: реальные размерные объекты, без ложного success."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .sketch import Sketch

KO_LDIM_PARAM = 45
KO_RDIM_PARAM = 54


def _ok(value: Any) -> bool:
    if value is None or value is False:
        return False
    try:
        return int(value) != 0
    except Exception:
        return True


def _kompas_object(sketch: "Sketch") -> Any:
    app = sketch._part.app
    for obj in (getattr(app, "k5", None), getattr(app, "app7", None)):
        if obj is None:
            continue
        for name in ("KompasObject", "ksObject", "Application"):
            try:
                k = getattr(obj, name, None)
                if k is not None:
                    return k() if callable(k) else k
            except Exception:
                continue
        if callable(getattr(obj, "GetParamStruct", None)):
            return obj
    return None


def _set(obj: Any, names: tuple[str, ...], value: Any) -> bool:
    for name in names:
        try:
            setattr(obj, name, value)
            return True
        except Exception:
            continue
    return False


def _init_param(ko: Any, type_id: int) -> Any:
    if ko is None:
        return None
    get_ps = getattr(ko, "GetParamStruct", None)
    if not callable(get_ps):
        return None
    try:
        param = get_ps(type_id)
    except Exception:
        return None
    if param is None:
        return None
    try:
        init = getattr(param, "Init", None)
        if callable(init):
            init()
    except Exception:
        pass
    return param


def linear_dimension(
    sketch: "Sketch",
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    text_x: Optional[float] = None,
    text_y: Optional[float] = None,
) -> bool:
    """Create a real API5 linear dimension attached to the given source points."""
    doc2d = sketch._ensure()
    ko = _kompas_object(sketch)
    param = _init_param(ko, KO_LDIM_PARAM)
    if param is None:
        return False

    source = None
    for getter in ("GetSPar", "GetSPar1", "SPar"):
        try:
            g = getattr(param, getter, None)
            source = g() if callable(g) else g
            if source is not None:
                break
        except Exception:
            continue
    if source is None:
        return False

    tx = float(text_x) if text_x is not None else (float(x1) + float(x2)) / 2.0
    ty = float(text_y) if text_y is not None else (float(y1) + float(y2)) / 2.0 + 8.0
    required = (
        ("x1", float(x1)), ("y1", float(y1)),
        ("x2", float(x2)), ("y2", float(y2)),
        ("dx", float(tx - x1)), ("dy", float(ty - y1)),
    )
    for name, value in required:
        _set(source, (name, name.upper()), value)
    _set(source, ("basePoint", "BasePoint"), 1)
    try:
        init = getattr(source, "Init", None)
        if callable(init):
            init()
    except Exception:
        pass

    drawing = None
    for getter in ("GetDPar", "GetDPar1", "DPar"):
        try:
            g = getattr(param, getter, None)
            drawing = g() if callable(g) else g
            if drawing is not None:
                break
        except Exception:
            continue
    if drawing is not None:
        # These fields are version-tolerant; KOMPAS can choose the final text
        # placement if a drawing field is unavailable.
        _set(drawing, ("x", "X", "x1", "X1"), tx)
        _set(drawing, ("y", "Y", "y1", "Y1"), ty)

    fn = getattr(doc2d, "ksLinDimension", None)
    if not callable(fn):
        return False
    try:
        return _ok(fn(param))
    except Exception:
        return False


def radial_dimension(
    sketch: "Sketch",
    xc: float,
    yc: float,
    radius: float,
    *,
    text_x: Optional[float] = None,
    text_y: Optional[float] = None,
    diameter: bool = True,
) -> bool:
    """Create a real API5 radial/diametric dimension for a circular source."""
    if radius <= 0:
        return False
    doc2d = sketch._ensure()
    ko = _kompas_object(sketch)
    param = _init_param(ko, KO_RDIM_PARAM)
    if param is None:
        return False

    source = None
    for getter in ("GetSPar", "GetSPar1", "SPar"):
        try:
            g = getattr(param, getter, None)
            source = g() if callable(g) else g
            if source is not None:
                break
        except Exception:
            continue
    if source is None:
        return False

    tx = float(text_x) if text_x is not None else float(xc) + float(radius) + 8.0
    ty = float(text_y) if text_y is not None else float(yc) + 8.0
    for name, value in (
        ("x1", float(xc)), ("y1", float(yc)),
        ("x2", float(xc + radius)), ("y2", float(yc)),
        ("dx", float(tx - xc)), ("dy", float(ty - yc)),
    ):
        _set(source, (name, name.upper()), value)
    try:
        init = getattr(source, "Init", None)
        if callable(init):
            init()
    except Exception:
        pass

    # Tell KOMPAS to use a diameter sign when the parameter object exposes it.
    if diameter:
        _set(param, ("type", "Type", "dimType", "DimType"), 1)

    fn = getattr(doc2d, "ksDiamDimension", None)
    if diameter and callable(fn):
        try:
            return _ok(fn(param))
        except Exception:
            pass
    for name in ("ksRadDimension", "ksRDimension"):
        fn = getattr(doc2d, name, None)
        if callable(fn):
            try:
                return _ok(fn(param))
            except Exception:
                continue
    return False


def try_auto_dim_circle(sketch: "Sketch", xc: float, yc: float, radius: float) -> bool:
    return radial_dimension(sketch, xc, yc, radius, diameter=True)


def try_auto_dim_rect(sketch: "Sketch", x: float, y: float, w: float, h: float) -> bool:
    ok1 = linear_dimension(sketch, x, y, x + w, y, text_y=y - 8)
    ok2 = linear_dimension(sketch, x, y, x, y + h, text_x=x - 8)
    return ok1 and ok2
