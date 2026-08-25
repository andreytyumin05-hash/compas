"""
Реальные константы КОМПАС из typelib + запасные значения.
"""

from __future__ import annotations

from typing import Any, Dict

try:
    from win32com.client import gencache
except ImportError:
    gencache = None  # type: ignore

_CONST3D_GUID = "{2CAF168C-7961-4B90-9DA2-701419BEEFE3}"

# Запасные id (типичные для API КОМПАС; уточняются из typelib если доступен)
_FALLBACK: Dict[str, int] = {
    "o3d_planeXOY": 1,
    "o3d_planeXOZ": 2,
    "o3d_planeYOZ": 3,
    "o3d_sketch": 5,
    "o3d_bossExtrusion": 25,
    "o3d_cutExtrusion": 26,
    "o3d_bossRotated": 27,
    "dtNormal": 0,
    "dtReverse": 1,
    "dtBoth": 2,
    "etBlind": 0,
    "etThroughAll": 1,
}


class KompasConstants:
    def __init__(self) -> None:
        self._vals: Dict[str, int] = dict(_FALLBACK)
        self._source = "fallback"
        self._load_typelib()

    def _load_typelib(self) -> None:
        if gencache is None:
            return
        try:
            mod = gencache.EnsureModule(_CONST3D_GUID, 0, 1, 0)
            c = mod.constants
            for key in list(self._vals.keys()):
                if hasattr(c, key):
                    self._vals[key] = int(getattr(c, key))
            self._source = "typelib"
        except Exception:
            self._source = "fallback"

    def get(self, name: str) -> int:
        if name not in self._vals:
            raise KeyError(name)
        return self._vals[name]

    def __getattr__(self, name: str) -> int:
        if name.startswith("_"):
            raise AttributeError(name)
        try:
            return self.get(name)
        except KeyError as e:
            raise AttributeError(name) from e

    @property
    def source(self) -> str:
        return self._source


# один экземпляр на процесс
CONST3D = KompasConstants()
