"""API5 размеры эскиза (ksLinDimension / diam).

Константы из Kompas6Constants:
  ko_LDimParam  = 0x2D = 45

Рабочий паттерн (форум ASCON / SDK):
  param = k5.GetParamStruct(45)
  dPar = param.GetDPar(); dPar.Init()
  sPar = param.GetSPar(); sPar.Init()
  tPar = param.GetTPar(); tPar.Init(0)   # важно: 0/False
  sPar.x1,y1,x2,y2; sPar.ps; sPar.dx,dy; sPar.basePoint=1
  doc2d.ksLinDimension(param)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable, Optional, Sequence, Tuple

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .sketch import Sketch

_KO_LDIM = (45,)
_KO_RDIM = (54, 26, 14)
_KO_DDIM = (53, 25, 13)


def _ok(value: Any) -> bool:
    if value is None or value is False:
        return False
    try:
        return int(value) != 0
    except Exception:
        return True


def _kompas_object(sketch: "Sketch") -> Any:
    """Только Application.5 (k5) — GetParamStruct живёт здесь."""
    app = sketch._part.app
    k5 = getattr(app, "k5", None)
    if k5 is not None and callable(getattr(k5, "GetParamStruct", None)):
        return k5
    for obj in (getattr(app, "app7", None),):
        if obj is None:
            continue
        if callable(getattr(obj, "GetParamStruct", None)):
            return obj
        for name in ("KompasObject", "ksObject", "Application"):
            try:
                k = getattr(obj, name, None)
                if k is None:
                    continue
                cand = k() if callable(k) else k
                if callable(getattr(cand, "GetParamStruct", None)):
                    return cand
            except Exception:
                continue
    return None


def _set(obj: Any, names: Sequence[str], value: Any) -> bool:
    for name in names:
        try:
            setattr(obj, name, value)
            return True
        except Exception:
            pass
        setter = "Set" + name[:1].upper() + name[1:]
        try:
            fn = getattr(obj, setter, None)
            if callable(fn):
                fn(value)
                return True
        except Exception:
            pass
    return False


def _call_init(obj: Any, *args: Any) -> None:
    if obj is None:
        return
    init = getattr(obj, "Init", None)
    if not callable(init):
        return
    try:
        if args:
            init(*args)
        else:
            init()
    except TypeError:
        try:
            init(0)
        except Exception:
            try:
                init(False)
            except Exception:
                pass
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


def _orientation_ps(x1: float, y1: float, x2: float, y2: float) -> Tuple[int, float, float]:
    dx = x2 - x1
    dy = y2 - y1
    if abs(dy) < 1e-9 and abs(dx) > 1e-9:
        return 0, 0.0, 10.0
    if abs(dx) < 1e-9 and abs(dy) > 1e-9:
        return 1, 10.0, 0.0
    return 2, 0.0, 10.0


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
    param = _init_param(ko, _KO_LDIM)
    if param is None:
        if strict:
            raise KompasOperationError("dim_linear: GetParamStruct(ko_LDimParam=45) недоступен")
        return False

    source = _get_sub(param, ("GetSPar", "GetSPar1", "SPar", "sPar"))
    drawing = _get_sub(param, ("GetDPar", "GetDPar1", "DPar", "dPar"))
    text = _get_sub(param, ("GetTPar", "GetTPar1", "TPar", "tPar"))
    if source is None:
        if strict:
            raise KompasOperationError("dim_linear: GetSPar failed")
        return False

    x1, y1, x2, y2 = map(float, (x1, y1, x2, y2))
    ps, def_dx, def_dy = _orientation_ps(x1, y1, x2, y2)
    if abs(def_dx) > 1e-12:
        def_dx = offset if def_dx > 0 else -offset
    if abs(def_dy) > 1e-12:
        def_dy = offset if def_dy > 0 else -offset

    if text_x is not None or text_y is not None:
        mx = (x1 + x2) / 2.0
        my = (y1 + y2) / 2.0
        def_dx = float(text_x) - mx if text_x is not None else def_dx
        def_dy = float(text_y) - my if text_y is not None else def_dy
        ps = 3

    _call_init(source)
    for name, val in (("x1", x1), ("y1", y1), ("x2", x2), ("y2", y2)):
        _set(source, (name, name.upper()), val)
    _set(source, ("basePoint", "BasePoint"), 1)
    _set(source, ("dx", "Dx"), float(def_dx))
    _set(source, ("dy", "Dy"), float(def_dy))
    _set(source, ("ps", "Ps"), int(ps))

    if drawing is not None:
        _call_init(drawing)
        _set(drawing, ("ang", "Ang"), 0)
        _set(drawing, ("lenght", "length", "Length"), 0)
        _set(drawing, ("pl1", "Pl1"), False)
        _set(drawing, ("pl2", "Pl2"), False)
        _set(drawing, ("pt1", "Pt1"), 1)
        _set(drawing, ("pt2", "Pt2"), 1)
        _set(drawing, ("shelfDir", "ShelfDir"), 0)
        _set(drawing, ("textBase", "TextBase"), 0)
        _set(drawing, ("textPos", "TextPos"), 0)

    if text is not None:
        _call_init(text, 0)
        _set(text, ("bitFlag", "BitFlag"), 1)
        _set(text, ("sign", "Sign"), 0)
        _set(text, ("style", "Style"), 3)
        _set(text, ("stringFlag", "StringFlag"), False)
        try:
            sbf = getattr(text, "SetBitFlagValue", None)
            if callable(sbf):
                sbf(1, True)
        except Exception:
            pass

    fn = getattr(doc2d, "ksLinDimension", None)
    if not callable(fn):
        if strict:
            raise KompasOperationError("dim_linear: ksLinDimension отсутствует на doc2d")
        return False
    try:
        result = fn(param)
        ok = _ok(result)
    except Exception as e:
        if strict:
            raise KompasOperationError(f"dim_linear: {e}") from e
        return False
    if not ok and strict:
        raise KompasOperationError(f"dim_linear: ksLinDimension вернул {result!r}")
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
    type_ids = tuple(_KO_DDIM if diameter else _KO_RDIM) + tuple(
        _KO_RDIM if diameter else _KO_DDIM
    )

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

        text = _get_sub(param, ("GetTPar", "GetTPar1", "TPar", "tPar"))
        if text is not None:
            _call_init(text, 0)
            _set(text, ("bitFlag", "BitFlag"), 1)
            try:
                sbf = getattr(text, "SetBitFlagValue", None)
                if callable(sbf):
                    sbf(1, True)
            except Exception:
                pass

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
        raise KompasOperationError("dim_radial: diam/rad и linear fallback не сработали")
    return ok


def try_auto_dim_rect(sketch: "Sketch", x: float, y: float, w: float, h: float) -> bool:
    a = linear_dimension(sketch, x, y, x + w, y, offset=8.0)
    b = linear_dimension(sketch, x, y, x, y + h, offset=8.0)
    return bool(a or b)


def try_auto_dim_circle(sketch: "Sketch", xc: float, yc: float, radius: float) -> bool:
    return radial_dimension(sketch, xc, yc, radius, diameter=True)
