"""Экспериментальные фаска/скругление (ID зависят от версии КОМПАС)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part

O3D_CHAMFER = 33
O3D_FILLET = 34


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
    if callable(c):
        try:
            c()
        except Exception:
            pass


def try_chamfer(part: "Part", size: float) -> Any:
    try:
        entity = part._part.NewEntity(O3D_CHAMFER)
    except Exception as e:
        raise KompasOperationError(f"Фаска NewEntity: {e}") from e
    if entity is None:
        raise KompasOperationError("NewEntity(chamfer) None")
    try:
        definition = _definition(entity)
        for fn in (
            lambda: setattr(definition, "length1", float(size)),
            lambda: setattr(definition, "Length1", float(size)),
        ):
            try:
                fn()
                break
            except Exception:
                continue
        _create(entity)
        return entity
    except Exception as e:
        raise KompasOperationError(f"Фаска: {e}") from e


def try_fillet(part: "Part", radius: float) -> Any:
    try:
        entity = part._part.NewEntity(O3D_FILLET)
    except Exception as e:
        raise KompasOperationError(f"Скругление NewEntity: {e}") from e
    if entity is None:
        raise KompasOperationError("NewEntity(fillet) None")
    try:
        definition = _definition(entity)
        for fn in (
            lambda: setattr(definition, "radius", float(radius)),
            lambda: setattr(definition, "Radius", float(radius)),
        ):
            try:
                fn()
                break
            except Exception:
                continue
        _create(entity)
        return entity
    except Exception as e:
        raise KompasOperationError(f"Скругление: {e}") from e
