"""
Фаска и скругление — API5 КОМПАС v23.

Важно (как ActiveDocument3D): GetDefinition — PROPERTY, не метод.
  definition = entity.GetDefinition   # без ()
  arr = definition.array()            # array — обычно метод
  arr.Clear(); arr.Add(edge)
  entity.Create
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .edges import EdgeSet, get_edges
from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

O3D_CHAMFER = 33
O3D_FILLET = 34


def _as_prop(obj: Any, name: str) -> Any:
    """Читать член строго как свойство (не вызывать)."""
    try:
        return getattr(obj, name)
    except Exception as e:
        raise KompasOperationError(f"{name}: {e}") from e


def _maybe_call(obj: Any) -> Any:
    """Если COM-объект иногда callable — пробуем (), при MEMBERNOTFOUND оставляем как есть."""
    if obj is None:
        return None
    if not callable(obj):
        return obj
    try:
        return obj()
    except Exception:
        return obj


def _definition(entity: Any) -> Any:
    """
    GetDefinition на ksEntity в late-binding — property.
    Вызов d() → DISP_E_MEMBERNOTFOUND (как Document3D()).
    """
    d = _as_prop(entity, "GetDefinition")
    if d is None:
        raise KompasOperationError("GetDefinition вернул None")
    return d


def _create(entity: Any) -> None:
    """Create тоже часто property-style: entity.Create без ()."""
    try:
        c = getattr(entity, "Create", None)
        if c is None:
            raise KompasOperationError("Create отсутствует")
        if callable(c):
            try:
                ok = c()
                if ok is False or ok == 0:
                    raise KompasOperationError("Create() вернул False/0")
            except TypeError:
                # уже «сработало» как property при getattr
                pass
            except KompasOperationError:
                raise
            except Exception as e:
                # MEMBERNOTFOUND при () — считаем property уже прочитан
                if "член группы" in str(e).lower() or "MEMBERNOTFOUND" in str(e).upper():
                    pass
                else:
                    raise KompasOperationError(f"Create: {e}") from e
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Create: {e}") from e


def _new_entity(part_com: Any, type_id: int, label: str) -> Any:
    try:
        ent = part_com.NewEntity(int(type_id))
    except Exception as e:
        raise KompasOperationError(f"{label} NewEntity({type_id}): {e}") from e
    if ent is None:
        raise KompasOperationError(f"{label} NewEntity({type_id}) = None")
    return ent


def _operation_edge_array(definition: Any) -> Any:
    errors = []
    for name in ("array", "Array", "GetArray", "EdgeArray", "GetArrayOfEdges"):
        try:
            attr = getattr(definition, name, None)
            if attr is None:
                continue
            # array() в примерах SDK — метод; если property — берём как есть
            if callable(attr):
                try:
                    arr = attr()
                except Exception as e:
                    errors.append(f"{name}(): {e}")
                    arr = attr  # fallback property
            else:
                arr = attr
            if arr is not None:
                return arr
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise KompasOperationError(
        "definition.array() недоступен. " + "; ".join(errors[:4])
    )


def _attach_edges(definition: Any, edges: EdgeSet) -> None:
    coms = edges.com_objects()
    if not coms:
        raise KompasOperationError("Пустой EdgeSet")

    arr = _operation_edge_array(definition)

    for m in ("Clear", "clear", "RemoveAll"):
        try:
            fn = getattr(arr, m, None)
            if callable(fn):
                try:
                    fn()
                except Exception:
                    pass
                break
            elif fn is not None:
                break
        except Exception:
            continue

    added = 0
    last_err = None
    for c in coms:
        ok_one = False
        for m in ("Add", "add", "Insert"):
            try:
                fn = getattr(arr, m, None)
                if not callable(fn):
                    continue
                fn(c)
                added += 1
                ok_one = True
                break
            except Exception as e:
                last_err = e
        if not ok_one and last_err:
            continue

    if added == 0:
        raise KompasOperationError(
            f"array.Add не принял рёбра ({len(coms)} шт). last={last_err}"
        )


def _set_fillet_radius(definition: Any, radius: float) -> None:
    errors = []
    for label, fn in (
        ("radius", lambda: setattr(definition, "radius", float(radius))),
        ("Radius", lambda: setattr(definition, "Radius", float(radius))),
        ("SetRadius", lambda: definition.SetRadius(float(radius))),
        ("SetFilletParam", lambda: definition.SetFilletParam(float(radius), True)),
    ):
        try:
            fn()
            return
        except Exception as e:
            errors.append(f"{label}: {e}")
    raise KompasOperationError(f"radius={radius}: " + "; ".join(errors[:4]))


def _set_chamfer_size(definition: Any, distance: float) -> None:
    d = float(distance)
    errors = []
    for label, fn in (
        ("SetChamferParam(T,d,d)", lambda: definition.SetChamferParam(True, d, d)),
        ("SetChamferParam(1,d,d)", lambda: definition.SetChamferParam(1, d, d)),
        ("SetChamferParametrs", lambda: definition.SetChamferParametrs(True, d, d)),
        (
            "length1/2",
            lambda: (
                setattr(definition, "length1", d),
                setattr(definition, "length2", d),
            ),
        ),
        (
            "Length1/2",
            lambda: (
                setattr(definition, "Length1", d),
                setattr(definition, "Length2", d),
            ),
        ),
    ):
        try:
            fn()
            return
        except Exception as e:
            errors.append(f"{label}: {e}")
    raise KompasOperationError(f"distance={distance}: " + "; ".join(errors[:5]))


def apply_fillet(part: "Part", edges: EdgeSet, radius: float) -> Any:
    if radius <= 0:
        raise KompasOperationError(f"fillet: radius > 0, got {radius}")
    if len(edges) == 0:
        raise KompasOperationError("fillet: пустой EdgeSet")

    entity = _new_entity(part._part, O3D_FILLET, "fillet")
    definition = _definition(entity)
    try:
        try:
            _attach_edges(definition, edges)
            _set_fillet_radius(definition, radius)
        except KompasOperationError:
            _set_fillet_radius(definition, radius)
            _attach_edges(definition, edges)
        _create(entity)
        try:
            _as_prop(entity, "Update")
        except Exception:
            pass
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(
            f"Скругление R={radius}: {e}. Уменьшите радиус, если больше половины толщины."
        ) from e


def apply_chamfer(part: "Part", edges: EdgeSet, distance: float) -> Any:
    if distance <= 0:
        raise KompasOperationError(f"chamfer: distance > 0, got {distance}")
    if len(edges) == 0:
        raise KompasOperationError("chamfer: пустой EdgeSet")

    entity = _new_entity(part._part, O3D_CHAMFER, "chamfer")
    definition = _definition(entity)
    try:
        try:
            _attach_edges(definition, edges)
            _set_chamfer_size(definition, distance)
        except KompasOperationError:
            _set_chamfer_size(definition, distance)
            _attach_edges(definition, edges)
        try:
            definition.SetTangent(False)
        except Exception:
            pass
        _create(entity)
        try:
            _as_prop(entity, "Update")
        except Exception:
            pass
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"Фаска d={distance}: {e}") from e


def try_chamfer(part: "Part", size: float) -> Any:
    return apply_chamfer(part, get_edges(part._part, "all"), size)


def try_fillet(part: "Part", radius: float) -> Any:
    return apply_fillet(part, get_edges(part._part, "all"), radius)
