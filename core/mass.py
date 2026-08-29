"""Масса / объём / центр масс — best-effort через COM."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional

from .exceptions import KompasOperationError

if TYPE_CHECKING:
    from .part import Part


def get_mass_properties(part: "Part") -> Dict[str, Any]:
    """
    Попытка получить массу, объём, центр масс.

    Returns dict keys: mass, volume, center (x,y,z) — что удалось.
    Если API недоступен — KompasOperationError с пояснением.

    Example:
        props = part.mass_properties()
        print(props.get("mass"), props.get("volume"))
    """
    result: Dict[str, Any] = {}
    p = part._part
    errors = []

    for attr in ("GetMassInertia", "GetMass", "mass", "Mass"):
        try:
            val = getattr(p, attr, None)
            if val is None:
                continue
            if callable(val):
                try:
                    out = val()
                except TypeError:
                    # иногда нужен буфер/флаги — пропускаем
                    continue
                result["raw"] = out
                break
            else:
                result["mass"] = float(val)
                break
        except Exception as e:
            errors.append(f"{attr}: {e}")

    for attr in ("volume", "Volume", "GetVolume"):
        try:
            val = getattr(p, attr, None)
            if val is None:
                continue
            result["volume"] = float(val() if callable(val) else val)
            break
        except Exception as e:
            errors.append(f"{attr}: {e}")

    if not result:
        raise KompasOperationError(
            "Массовые характеристики недоступны через текущий COM-binding. "
            f"Попробуйте вручную в КОМПАС. ({'; '.join(errors[:3])})"
        )
    return result
