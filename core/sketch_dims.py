"""API5 размеры эскиза — привязка к точкам геометрии (не «декор»).

По форуму ASCON / SDK:
  param = KompasObject.GetParamStruct(ko_LDimParam)
  source = param.GetSPar(); source.Init()
  source.x1,y1,x2,y2 — концы измеряемого отрезка (те же, что у ksLineSeg)
  source.dx, dy — смещение размерной линии от basePoint
  source.ps = 2 — размер параллелен отрезку
  doc2d.ksLinDimension(param)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Optional, Sequence

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .sketch import Sketch

_KO_LDIM_CANDIDATES = (45, 24, 9)
_KO_RDIM_CANDIDATES = (54, 26, 14)
_KO_DDIM_CANDIDATES = (53, 25, 13)


def _ok(value: Any) -> bool:
    if value is None or value is False:
        return False
    try:
        return int(value) != 0
    except Exception:
        return True


def _kompas_object(sketch: "Sketch") -> Any:
    app = sketch._part.app
    candidates = []
    for obj in (getattr(app, "k5", None), getattr(app, "app7", None)):
        if obj is None:
            continue
        candidates.append(obj)
        for name in ("KompasObject", "ksObject"):
            try:
                k = getattr(obj, name, None)
                if k is None:
                    continue
                candidates.append(k() if callable(k) else k)
            except Exception:
                continue
    for obj in candidates:
        if obj is None:
            continue
        if callable(getattr(obj, "GetParamStruct", None)):
            return obj
    return None


def _set(obj: Any, names: Sequence[str], value: Any) -> bool:
    for name in names:
        try:
            setattr(obj, name, value)
            return True
        except Exception:
            continue
    return False


def _call_init(obj: Any) -> None:
    if obj is None:
        return
    try:
        init = getattr(obj, "Init", None)
        if callable(init):
            try:
                init()
            except TypeError:
                init(0)
    except Exception:
        pass


def _get_sub(param: Any, getters: Sequence[str]) -> Any:
    for getter in getters:
        try:
            g = getattr(param, getter, None)
            if g is None:
                continue
            v = g() if callable(g) else g
            if v is not None:
                return v
        except Exception:
            continue
    return None


def _init_param(ko: Any, type_ids: Iterable[int]) -> Any:
    if ko is None:
        return None
    get_ps = getattr(ko, "GetParamStruct", None)
    if not callable(get_ps):
        return None
    for type_id in type_ids:
        try:
            param = get_ps(int(type_id))
        except Exception:
            continue
        if param is None:
            continue
        _call_init(param)
        return param
    return None


def linear_dimension(
    sketch: "Sketch",
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    *,
    text_x: Optional[float] = None,
    text_y: Optional[float] = None,
    offset: float = 10.0,
    strict: bool = False,
) -> bool:
    doc2d = sketch._ensure()
    ko = _kompas_object(sketch)
    param = _init_param(ko, _KO_LDIM_CANDIDATES)
    if param is None:
        if strict:
            raise KompasOperationError("dim_linear: GetParamStruct(ko_LDimParam) недоступен")
        return False

    source = _get_sub(param, ("GetSPar", "GetSPar1", "SPar", "sPar"))
    if source is None:
        if strict:
            raise KompasOperationError("dim_linear: GetSPar failed")
        return False

    _call_init(source)
    x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
    for name, val in (("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)):
        _set(source, (name, name.upper()), val)

    _set(source, ("basePoint", "BasePoint"), 1)
    _set(source, ("dx", "Dx"), 0.0)
    _set(source, ("dy", "Dy"), float(offset))
    _set(source, ("ps", "Ps"), 2)

    drawing = _get_sub(param, ("GetDPar", "GetDPar1", "DPar", "dPar"))
    if drawing is not None:
        _call_init(drawing)
        _set(drawing, ("ang", "Ang"), 0)
        _set(drawing, ("lenght", "length", "Length"), 0)
        _set(drawing, ("pl1", "Pl1"), False)
        _set(drawing, ("pl2", "Pl2"), False)
        _set(drawing, ("pt1", "Pt1"), 1)
        _set(drawing, ("pt2", "Pt2"), 1)

    text = _get_sub(param, ("GetTPar", "GetTPar1", "TPar", "tPar"))
    if text is not None:
        _call_init(text)
        _set(text, ("bitFlag", "BitFlag"), 1)
        _set(text, ("sign", "Sign"), 0)
        _set(text, ("style", "Style"), 3)
        _set(text, ("stringFlag", "StringFlag"), False)

    fn = getattr(doc2d, "ksLinDimension", None)
    if not callable(fn):
        if strict:
            raise KompasOperationError("dim_linear: ksLinDimension отсутствует")
        return False
    try:
        ok = _ok(fn(param))
    except Exception as e:
        if strict:
            raise KompasOperationError(f"dim_linear: {e}") from e
        return False
    if not ok and strict:
        raise KompasOperationError("dim_linear: ksLinDimension вернул 0")
    return ok


def radial_dimension(
    sketch: "Sketch",
    xc: float,
    yc: float,
    radius: float,
    *,
    text_x: Optional[float] = None,
    text_y: Optional[float] = None,
    diameter: bool = True,
    strict: bool = False,
) -> bool:
    if radius <= 0:
        return False
    doc2d = sketch._ensure()
    ko = _kompas_object(sketch)
    type_ids = tuple(_KO_DDIM_CANDIDATES if diameter else _KO_RDIM_CANDIDATES)
    type_ids = type_ids + tuple(_KO_RDIM_CANDIDATES if diameter else _KO_DDIM_CANDIDATES)

    param = _init_param(ko, type_ids)
    xc, yc, radius = float(xc), float(yc), float(radius)
    tx = float(text_x) if text_x is not None else xc + radius * 1.2
    ty = float(text_y) if text_y is not None else yc

    if param is not None:
        source = _get_sub(param, ("GetSPar", "GetSPar1", "SPar", "sPar"))
        if source is not None:
            _call_init(source)
            _set(source, ("xc", "Xc", "x1", "X1"), xc)
            _set(source, ("yc", "Yc", "y1", "Y1"), yc)
            _set(source, ("x2", "X2"), xc + radius)
            _set(source, ("y2", "Y2"), yc)
            _set(source, ("radius", "Radius", "r", "R"), radius)
            _set(source, ("dx", "Dx"), float(tx - xc))
            _set(source, ("dy", "Dy"), float(ty - yc))

        drawing = _get_sub(param, ("GetDPar", "GetDPar1", "DPar"))
        if drawing is not None:
            _call_init(drawing)

        for method in ("ksDiamDimension", "ksRadDimension", "ksRDimension"):
            fn = getattr(doc2d, method, None)
            if not callable(fn):
                continue
            try:
                if _ok(fn(param)):
                    return True
            except Exception:
                continue

    ok = linear_dimension(
        sketch, xc - radius, yc, xc + radius, yc, offset=12.0, strict=False
    )
    if not ok and strict:
        raise KompasOperationError("dim_radial: ни diam/rad, ни linear fallback")
    return ok


def try_auto_dim_rect(sketch: "Sketch", x: float, y: float, w: float, h: float) -> bool:
    a = linear_dimension(sketch, x, y, x + w, y, offset=8.0)
    b = linear_dimension(sketch, x, y, x, y + h, offset=8.0)
    return bool(a or b)


def try_auto_dim_circle(sketch: "Sketch", xc: float, yc: float, radius: float) -> bool:
    return radial_dimension(sketch, xc, yc, radius, diameter=True)
