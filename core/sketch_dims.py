"""
Размеры в эскизе (API5, best-effort).

На многих установках без typelib GetParamStruct/ksLinDimension нестабильны.
Методы НЕ обязаны успеть: при сбое возвращают False, геометрию не ломают.

Цель v1: заложить API для агента; v2 — управляющие размеры + внешние переменные.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from .sketch import Sketch


def _kompas_object(sketch: "Sketch") -> Any:
    app = sketch._part.app
    for obj in (getattr(app, "k5", None), getattr(app, "app7", None)):
        if obj is None:
            continue
        for name in ("KompasObject", "ksObject", "Application"):
            try:
                k = getattr(obj, name, None)
                if k is not None:
                    return k if not callable(k) else k()
            except Exception:
                continue
        return obj
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
) -> bool:
    """Линейный размер между двумя точками (управляющий, если API позволит)."""
    doc2d = sketch._ensure()
    ko = _kompas_object(sketch)
    tx = text_x if text_x is not None else (float(x1) + float(x2)) / 2.0
    ty = text_y if text_y is not None else (float(y1) + float(y2)) / 2.0 + 8.0

    # Вариант 1: короткий вызов, если есть
    for name in ("ksLinDimension", "ksLineDimension"):
        fn = getattr(doc2d, name, None)
        if callable(fn):
            try:
                # некоторые сборки принимают упрощённую сигнатуру
                r = fn(float(x1), float(y1), float(x2), float(y2), float(tx), float(ty))
                if r not in (0, None, False):
                    return True
            except Exception:
                pass

    if ko is None:
        return False

    try:
        # Классический путь API5 через param struct
        get_ps = getattr(ko, "GetParamStruct", None)
        if not callable(get_ps):
            return False
        # ko_LDimParam ≈ 21 в старых константах; пробуем число и имя
        param = None
        for key in (21, "ko_LDimParam", 20):
            try:
                param = get_ps(key)
                if param is not None:
                    break
            except Exception:
                continue
        if param is None:
            return False

        # Заполняем поля через late binding — имена различаются по версиям
        spar = None
        for getter in ("GetSPar", "SPar", "GetSourceParam"):
            try:
                g = getattr(param, getter, None)
                spar = g() if callable(g) else g
                if spar is not None:
                    break
            except Exception:
                continue
        if spar is not None:
            for attr, val in (
                ("x1", float(x1)),
                ("y1", float(y1)),
                ("x2", float(x2)),
                ("y2", float(y2)),
                ("dx", float(tx - x1)),
                ("dy", float(ty - y1)),
                ("basePoint", 1),
                ("ps", 1),
            ):
                try:
                    setattr(spar, attr, val)
                except Exception:
                    pass
            try:
                init = getattr(spar, "Init", None)
                if callable(init):
                    init()
            except Exception:
                pass

        r = doc2d.ksLinDimension(param)
        return r not in (0, None, False)
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
) -> bool:
    """Радиальный/диаметральный размер окружности (best-effort)."""
    doc2d = sketch._ensure()
    tx = text_x if text_x is not None else float(xc) + float(radius) + 5.0
    ty = text_y if text_y is not None else float(yc) + 5.0

    for name in ("ksRadDimension", "ksRDimension", "ksDiamDimension"):
        fn = getattr(doc2d, name, None)
        if callable(fn):
            try:
                r = fn(float(xc), float(yc), float(radius), float(tx), float(ty))
                if r not in (0, None, False):
                    return True
            except Exception:
                try:
                    r = fn(float(xc), float(yc), float(tx), float(ty))
                    if r not in (0, None, False):
                        return True
                except Exception:
                    pass
    # fallback: линейный размер по радиусу
    return linear_dimension(
        sketch, xc, yc, xc + radius, yc, text_x=tx, text_y=ty
    )


def try_auto_dim_circle(sketch: "Sketch", xc: float, yc: float, radius: float) -> bool:
    return radial_dimension(sketch, xc, yc, radius)


def try_auto_dim_rect(
    sketch: "Sketch", x: float, y: float, w: float, h: float
) -> bool:
    ok1 = linear_dimension(sketch, x, y, x + w, y, text_y=y - 8)
    ok2 = linear_dimension(sketch, x, y, x, y + h, text_x=x - 8)
    return ok1 or ok2
