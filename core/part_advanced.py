"""
Фаска и скругление — канон API5 КОМПАС v23:

  entity = part.NewEntity(o3d_fillet|o3d_chamfer)  # 34 | 33
  definition = entity.GetDefinition()
  edgeArr = definition.array()   # коллекция рёбер операции
  edgeArr.Clear()
  edgeArr.Add(edge)
  definition.radius = r  /  SetChamferParam(...)
  entity.Create()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional

from .edges import EdgeSet, get_edges
from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

O3D_CHAMFER = 33
O3D_FILLET = 34


def _definition(entity: Any) -> Any:
    """GetDefinition — method или property (как ActiveDocument3D)."""
    try:
        d = entity.GetDefinition
    except Exception as e:
        raise KompasOperationError(f"GetDefinition: {e}") from e
    # не вызывать callable вслепую, если это уже definition-объект
    if d is None:
        raise KompasOperationError("GetDefinition вернул None")
    # Если это метод без аргументов — один вызов
    try:
        # win32com: methods often need ()
        if callable(d):
            try:
                return d()
            except TypeError:
                return d
        return d
    except Exception as e:
        raise KompasOperationError(f"GetDefinition invoke: {e}") from e


def _create(entity: Any) -> None:
    c = getattr(entity, "Create", None)
    if c is None:
        raise KompasOperationError("entity.Create отсутствует")
    try:
        if callable(c):
            ok = c()
            if ok is False or ok == 0:
                raise KompasOperationError("entity.Create() вернул False/0")
        # иначе property-style уже сработал при getattr
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"entity.Create: {e}") from e


def _new_entity(part_com: Any, type_id: int, label: str) -> Any:
    try:
        ent = part_com.NewEntity(int(type_id))
    except Exception as e:
        raise KompasOperationError(f"{label} NewEntity({type_id}): {e}") from e
    if ent is None:
        raise KompasOperationError(f"{label} NewEntity({type_id}) вернул None")
    return ent


def _operation_edge_array(definition: Any) -> Any:
    """
    Коллекция рёбер операции: definition.array() — основной путь SDK.
    """
    errors = []
    for name in ("array", "Array", "GetArray", "EdgeArray", "GetArrayOfEdges"):
        try:
            attr = getattr(definition, name, None)
            if attr is None:
                continue
            arr = attr() if callable(attr) else attr
            if arr is not None:
                return arr
        except Exception as e:
            errors.append(f"{name}: {e}")
    raise KompasOperationError(
        "definition.array() недоступен для fillet/chamfer. "
        f"Детали: {'; '.join(errors) if errors else 'нет метода array'}"
    )


def _attach_edges(definition: Any, edges: EdgeSet) -> None:
    coms = edges.com_objects()
    if not coms:
        raise KompasOperationError("Пустой EdgeSet — нечего добавлять в фаску/скругление")

    arr = _operation_edge_array(definition)

    # Clear
    for m in ("Clear", "clear", "RemoveAll"):
        try:
            fn = getattr(arr, m, None)
            if callable(fn):
                fn()
                break
        except Exception:
            continue

    added = 0
    last_err = None
    for c in coms:
        for m in ("Add", "add", "Insert", "ksAddArrayItem"):
            try:
                fn = getattr(arr, m, None)
                if not callable(fn):
                    continue
                fn(c)
                added += 1
                break
            except Exception as e:
                last_err = e
                continue

    if added == 0:
        raise KompasOperationError(
            f"array.Add(edge) не принял ни одного ребра из {len(coms)}. last={last_err}"
        )


def _set_fillet_radius(definition: Any, radius: float) -> None:
    errors = []
    for attempt in (
        ("radius=", lambda: setattr(definition, "radius", float(radius))),
        ("Radius=", lambda: setattr(definition, "Radius", float(radius))),
        ("SetRadius", lambda: definition.SetRadius(float(radius))),
        ("SetFilletParam", lambda: definition.SetFilletParam(float(radius), True)),
        ("SetFilletParam2", lambda: definition.SetFilletParam(float(radius), False)),
    ):
        try:
            attempt[1]()
            return
        except Exception as e:
            errors.append(f"{attempt[0]}: {e}")
    raise KompasOperationError(
        f"Не задать radius={radius}. " + "; ".join(errors[:4])
    )


def _set_chamfer_size(definition: Any, distance: float) -> None:
    d = float(distance)
    errors = []
    # канон: SetChamferParam(EqualOrFirst, length1, length2)
    for attempt in (
        ("SetChamferParam(True,d,d)", lambda: definition.SetChamferParam(True, d, d)),
        ("SetChamferParam(1,d,d)", lambda: definition.SetChamferParam(1, d, d)),
        ("SetChamferParametrs", lambda: definition.SetChamferParametrs(True, d, d)),
        ("length1/2", lambda: (_set_both_lengths(definition, d))),
        ("SetChamferParam(False,d,d)", lambda: definition.SetChamferParam(False, d, d)),
    ):
        try:
            attempt[1]()
            return
        except Exception as e:
            errors.append(f"{attempt[0]}: {e}")
    raise KompasOperationError(
        f"Не задать фаску distance={distance}. " + "; ".join(errors[:5])
    )


def _set_both_lengths(definition: Any, d: float) -> None:
    ok = False
    for a, b in (("length1", "length2"), ("Length1", "Length2")):
        try:
            setattr(definition, a, d)
            setattr(definition, b, d)
            ok = True
            return
        except Exception:
            continue
    if not ok:
        raise RuntimeError("length1/length2 not settable")


def apply_fillet(part: "Part", edges: EdgeSet, radius: float) -> Any:
    if radius <= 0:
        raise KompasOperationError(f"fillet: radius > 0, получено {radius}")
    if len(edges) == 0:
        raise KompasOperationError("fillet: пустой набор рёбер")

    entity = _new_entity(part._part, O3D_FILLET, "fillet")
    try:
        definition = _definition(entity)
        # порядок как в примерах SDK: сначала рёбра, потом радиус (и наоборот — пробуем оба)
        try:
            _attach_edges(definition, edges)
            _set_fillet_radius(definition, radius)
        except KompasOperationError:
            _set_fillet_radius(definition, radius)
            _attach_edges(definition, edges)
        _create(entity)
        try:
            entity.Update
        except Exception:
            pass
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(
            f"Скругление radius={radius}: {e}. "
            "Если радиус больше половины толщины — уменьшите radius."
        ) from e


def apply_chamfer(part: "Part", edges: EdgeSet, distance: float) -> Any:
    if distance <= 0:
        raise KompasOperationError(f"chamfer: distance > 0, получено {distance}")
    if len(edges) == 0:
        raise KompasOperationError("chamfer: пустой набор рёбер")

    entity = _new_entity(part._part, O3D_CHAMFER, "chamfer")
    try:
        definition = _definition(entity)
        try:
            _attach_edges(definition, edges)
            _set_chamfer_size(definition, distance)
        except KompasOperationError:
            _set_chamfer_size(definition, distance)
            _attach_edges(definition, edges)
        # tangent optional
        try:
            definition.SetTangent(False)
        except Exception:
            try:
                definition.tangent = False
            except Exception:
                pass
        _create(entity)
        try:
            entity.Update
        except Exception:
            pass
        return entity
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(
            f"Фаска distance={distance}: {e}"
        ) from e


def try_chamfer(part: "Part", size: float) -> Any:
    edges = get_edges(part._part, "all")
    return apply_chamfer(part, edges, size)


def try_fillet(part: "Part", radius: float) -> Any:
    edges = get_edges(part._part, "all")
    return apply_fillet(part, edges, radius)
