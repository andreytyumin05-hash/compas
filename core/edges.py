"""
Выбор рёбер (API5). o3d_edge = 7.

First/Next/Count на коллекциях — часто PROPERTY (не вызывать ()).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

from .exceptions import KompasOperationError

O3D_EDGE = 7
O3D_FACE = 6


@dataclass
class EdgeRef:
    com: Any
    index: int = -1
    source: str = ""
    midpoint: Optional[Tuple[float, float, float]] = None
    direction: Optional[Tuple[float, float, float]] = None


@dataclass
class EdgeSet:
    edges: List[EdgeRef] = field(default_factory=list)
    filter_name: str = ""
    _raw_collection: Any = field(default=None, repr=False)

    def __len__(self) -> int:
        return len(self.edges)

    def __iter__(self):
        return iter(self.edges)

    def com_objects(self) -> List[Any]:
        return [e.com for e in self.edges if e.com is not None]


def _prop(obj: Any, name: str) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return None


def _collection_count(col: Any) -> Optional[int]:
    for cname in ("GetCount", "Count", "count"):
        try:
            c = getattr(col, cname)
            # GetCount иногда method
            if callable(c):
                try:
                    return int(c())
                except Exception:
                    try:
                        return int(c)
                    except Exception:
                        continue
            return int(c)
        except Exception:
            continue
    return None


def _collection_item(col: Any, i: int) -> Any:
    for iname, idx in (("Item", i), ("GetByIndex", i), ("Item", i - 1), ("GetByIndex", i - 1)):
        try:
            fn = getattr(col, iname, None)
            if fn is None:
                continue
            if callable(fn):
                try:
                    item = fn(idx)
                except Exception:
                    continue
            else:
                item = fn
            if item is not None:
                return item
        except Exception:
            continue
    return None


def _entity_collection(part_com: Any, type_id: int) -> Any:
    try:
        return part_com.EntityCollection(int(type_id))
    except Exception:
        return None


def _iter_collection_items(col: Any) -> List[Any]:
    if col is None:
        return []
    items: List[Any] = []
    n = _collection_count(col)
    if n is not None and n > 0:
        for i in range(1, n + 1):
            it = _collection_item(col, i)
            if it is not None:
                items.append(it)
        if items:
            return items
        for i in range(n):
            it = _collection_item(col, i)
            if it is not None:
                items.append(it)
        return items

    # First / Next как PROPERTY (не First())
    try:
        it = _prop(col, "First")
        guard = 0
        while it is not None and guard < 10000:
            items.append(it)
            it = _prop(col, "Next")
            guard += 1
    except Exception:
        pass
    return items


def collect_all_edges(part_com: Any) -> EdgeSet:
    col = _entity_collection(part_com, O3D_EDGE)
    if col is not None:
        raw_items = _iter_collection_items(col)
        if raw_items:
            edges = [
                EdgeRef(com=it, index=i, source="EntityCollection(7)")
                for i, it in enumerate(raw_items)
            ]
            return EdgeSet(edges=edges, filter_name="all", _raw_collection=col)

    face_col = _entity_collection(part_com, O3D_FACE)
    found: List[EdgeRef] = []
    seen: set = set()
    if face_col is not None:
        for fi, face in enumerate(_iter_collection_items(face_col)):
            ecol = None
            for name in ("EdgeCollection", "GetEdgeCollection", "Edges"):
                attr = _prop(face, name)
                if attr is None:
                    continue
                ecol = attr
                break
            if ecol is None:
                continue
            for edge in _iter_collection_items(ecol):
                key = id(edge)
                if key in seen:
                    continue
                seen.add(key)
                found.append(EdgeRef(com=edge, index=len(found), source=f"face[{fi}]"))

    if found:
        return EdgeSet(edges=found, filter_name="all")

    diag = []
    for tid, label in ((6, "face"), (7, "edge"), (8, "vertex")):
        c = _entity_collection(part_com, tid)
        diag.append(f"{label}({tid})={_collection_count(c)}")
    raise KompasOperationError(
        "Нет рёбер EntityCollection(7). " + ", ".join(diag)
    )


def select_edges_near_point(part_com: Any, x: float, y: float, z: float) -> EdgeSet:
    col = _entity_collection(part_com, O3D_EDGE)
    if col is None:
        raise KompasOperationError("EntityCollection(7) недоступна")

    for m in ("UnSelectAll", "Clear", "Refresh"):
        try:
            fn = getattr(col, m, None)
            if callable(fn):
                fn()
        except Exception:
            pass

    sel = getattr(col, "SelectByPoint", None)
    if not callable(sel):
        raise KompasOperationError("SelectByPoint нет")
    try:
        sel(float(x), float(y), float(z))
    except Exception as e:
        raise KompasOperationError(f"SelectByPoint: {e}") from e

    # First/Next — property
    items: List[Any] = []
    it = _prop(col, "First")
    guard = 0
    while it is not None and guard < 1000:
        items.append(it)
        it = _prop(col, "Next")
        guard += 1

    if not items:
        items = _iter_collection_items(col)

    if not items:
        raise KompasOperationError(f"SelectByPoint({x},{y},{z}): пусто")

    return EdgeSet(
        edges=[
            EdgeRef(com=it, index=i, source=f"SelectByPoint({x},{y},{z})")
            for i, it in enumerate(items)
        ],
        filter_name="near_point",
        _raw_collection=col,
    )


def get_edges(
    part_com: Any,
    filter: str = "all",
    *,
    point: Optional[Tuple[float, float, float]] = None,
    tol: float = 1.0,
) -> EdgeSet:
    pred = filter.lower().strip()
    if pred == "near_point":
        if point is None:
            raise KompasOperationError("near_point: point=(x,y,z)")
        return select_edges_near_point(part_com, point[0], point[1], point[2])
    if pred in ("all", "*", ""):
        return collect_all_edges(part_com)
    raise KompasOperationError(
        f"filter {filter!r}: на late-binding доступны all и near_point"
    )
