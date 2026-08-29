"""
Фаска и скругление с передачей EdgeSet (выбор рёбер).

Example:
    edges = part.get_edges("all")
    part.fillet(edges, radius=1.0)
    part.chamfer(edges, distance=0.5)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, List, Optional, Union

from .edges import EdgeSet, EdgeRef
from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

# Obj3dType — пробуем несколько id (зависят от версии SDK)
_O3D_CHAMFER_IDS = (33, 32, 45, 46)
_O3D_FILLET_IDS = (34, 35, 47, 48)


def _definition(entity: Any) -> Any:
    d = entity.GetDefinition
    if callable(d):
        try:
            return d()
        except Exception:
            return d
    return d


def _create(entity: Any) -> None:
    c = getattr(entity, "Create", None)
    if c is None:
        raise KompasOperationError("entity.Create отсутствует")
    if callable(c):
        ok = c()
        if ok is False:
            raise KompasOperationError("entity.Create() вернул False")
    # property-style: already invoked via getattr in some builds


def _new_entity(part_com: Any, type_ids: List[int], label: str) -> Any:
    last = None
    for tid in type_ids:
        try:
            ent = part_com.NewEntity(tid)
            if ent is not None:
                return ent
        except Exception as e:
            last = e
    raise KompasOperationError(
        f"{label}: NewEntity не создал объект (ids={type_ids}). last={last}"
    )


def _attach_edges(definition: Any, edges: EdgeSet) -> None:
    """Привязать рёбра к definition фаски/скругления — несколько путей SDK."""
    coms = edges.com_objects()
    if not coms:
        raise KompasOperationError("Нет COM-объектов рёбер в EdgeSet (пустой выбор)")

    errors = []

    # 1) AddArrayOfEdges / AddEdges
    for method in ("AddArrayOfEdges", "AddEdges", "SetEdges", "ChooseEdges"):
        try:
            fn = getattr(definition, method, None)
            if fn is None:
                continue
            if callable(fn):
                try:
                    fn(coms)
                    return
                except TypeError:
                    # по одному
                    for c in coms:
                        fn(c)
                    return
        except Exception as e:
            errors.append(f"{method}: {e}")

    # 2) EdgeArray / Edges collection on definition
    for attr in ("EdgeArray", "Edges", "EdgeCollection"):
        try:
            col = getattr(definition, attr, None)
            if col is None:
                continue
            if callable(col):
                col = col()
            for method in ("Add", "AddEdge", "Insert"):
                try:
                    add = getattr(col, method, None)
                    if add is None:
                        continue
                    for c in coms:
                        add(c)
                    return
                except Exception as e:
                    errors.append(f"{attr}.{method}: {e}")
        except Exception as e:
            errors.append(f"{attr}: {e}")

    # 3) CArray / ksEdgeArray style
    try:
        arr = getattr(definition, "GetArrayOfEdges", None) or getattr(
            definition, "ArrayOfEdges", None
        )
        if arr is not None:
            if callable(arr):
                arr = arr()
            for method in ("Add", "ksAddArrayItem", "Insert"):
                try:
                    add = getattr(arr, method, None)
                    if add is None:
                        continue
                    for c in coms:
                        add(c)
                    return
                except Exception as e:
                    errors.append(f"array.{method}: {e}")
    except Exception as e:
        errors.append(f"array path: {e}")

    raise KompasOperationError(
        "Не удалось привязать рёбра к операции фаски/скругления. "
        "COM-definition не принял AddArrayOfEdges/Edges.Add. "
        f"Рёбер в наборе: {len(coms)}. Детали: {'; '.join(errors[:6])}"
    )


def _set_chamfer_size(definition: Any, distance: float) -> None:
    for setter in (
        lambda: setattr(definition, "length1", float(distance)),
        lambda: setattr(definition, "Length1", float(distance)),
        lambda: setattr(definition, "length2", float(distance)),
        lambda: definition.SetChamferParam(float(distance), float(distance)),
        lambda: definition.SetChamferParametrs(True, float(distance), float(distance)),
    ):
        try:
            setter()
            return
        except Exception:
            continue
    raise KompasOperationError(
        f"Не задать размер фаски distance={distance} (ни length1, ни SetChamferParam)"
    )


def _set_fillet_radius(definition: Any, radius: float) -> None:
    for setter in (
        lambda: setattr(definition, "radius", float(radius)),
        lambda: setattr(definition, "Radius", float(radius)),
        lambda: definition.SetFilletParam(float(radius), True),
        lambda: definition.SetRadius(float(radius)),
    ):
        try:
            setter()
            return
        except Exception:
            continue
    raise KompasOperationError(
        f"Не задать радиус скругления radius={radius}"
    )


def apply_chamfer(part: "Part", edges: EdgeSet, distance: float) -> Any:
    if distance <= 0:
        raise KompasOperationError(
            f"Фаска: distance должен быть > 0, получено {distance}"
        )
    if len(edges) == 0:
        raise KompasOperationError("Фаска: пустой набор рёбер — сначала get_edges(...)" )

    entity = _new_entity(part._part, list(_O3D_CHAMFER_IDS), "chamfer")
    try:
        definition = _definition(entity)
        _set_chamfer_size(definition, distance)
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
        msg = str(e).lower()
        if "radius" in msg or "радиус" in msg or "толщин" in msg:
            raise KompasOperationError(
                f"Фаска distance={distance} отвергнута геометрией "
                f"(возможно больше половины толщины стенки): {e}"
            ) from e
        raise KompasOperationError(f"Фаска: {e}") from e


def apply_fillet(part: "Part", edges: EdgeSet, radius: float) -> Any:
    if radius <= 0:
        raise KompasOperationError(f"Скругление: radius > 0, получено {radius}")
    if len(edges) == 0:
        raise KompasOperationError("Скругление: пустой набор рёбер")

    entity = _new_entity(part._part, list(_O3D_FILLET_IDS), "fillet")
    try:
        definition = _definition(entity)
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
        msg = str(e).lower()
        if any(w in msg for w in ("radius", "радиус", "толщин", "невозмож")):
            raise KompasOperationError(
                f"Скругление radius={radius} невозможно на выбранных рёбрах "
                f"(часто радиус больше половины толщины/конфликтует с соседней геометрией): {e}"
            ) from e
        raise KompasOperationError(f"Скругление: {e}") from e


# backward-compatible names used earlier
def try_chamfer(part: "Part", size: float) -> Any:
    """Устарело: фаска по всем рёбрам. Предпочтительно part.chamfer(part.get_edges('all'), size)."""
    from .edges import get_edges

    edges = get_edges(part._part, "all")
    return apply_chamfer(part, edges, size)


def try_fillet(part: "Part", radius: float) -> Any:
    from .edges import get_edges

    edges = get_edges(part._part, "all")
    return apply_fillet(part, edges, radius)
