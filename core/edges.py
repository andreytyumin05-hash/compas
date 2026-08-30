"""
Выбор рёбер тела для фаски/скругления (КОМПАС API5).

Канон SDK:
  o3d_edge = 7, o3d_face = 6, o3d_vertex = 8
  part.EntityCollection(o3d_edge)
  collection.SelectByPoint(x, y, z)  # отбор у точки
  collection.First()

LLM работает с предикатами, не с сырыми ID.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, List, Optional, Sequence, Tuple

from .exceptions import KompasOperationError

# Obj3dType — правильный порядок: сначала РЕБРО, не вершина
O3D_EDGE = 7
O3D_FACE = 6
O3D_VERTEX = 8
_O3D_EDGE_CANDIDATES = (7,)  # только edge; 8 = vertex — НЕ использовать
_O3D_FACE_CANDIDATES = (6,)


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
    # сырая коллекция EntityCollection(o3d_edge) — для SelectByPoint
    _raw_collection: Any = field(default=None, repr=False)

    def __len__(self) -> int:
        return len(self.edges)

    def __iter__(self):
        return iter(self.edges)

    def com_objects(self) -> List[Any]:
        return [e.com for e in self.edges if e.com is not None]


def _vec_len(v: Sequence[float]) -> float:
    return math.sqrt(sum(float(x) * float(x) for x in v))


def _normalize(v: Sequence[float]) -> Optional[Tuple[float, float, float]]:
    L = _vec_len(v)
    if L < 1e-12:
        return None
    return (float(v[0]) / L, float(v[1]) / L, float(v[2]) / L)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])


def _collection_count(col: Any) -> Optional[int]:
    for cname in ("GetCount", "Count", "count"):
        try:
            c = getattr(col, cname)
            n = int(c() if callable(c) else c)
            return n
        except Exception:
            continue
    return None


def _collection_item(col: Any, i: int) -> Any:
    """1-based и 0-based Item."""
    for iname, idx in (("Item", i), ("GetByIndex", i), ("Item", i - 1), ("GetByIndex", i - 1)):
        try:
            fn = getattr(col, iname, None)
            if fn is None:
                continue
            item = fn(idx) if callable(fn) else None
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
        # KOMPAS часто 1-based
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
    # First / Next
    try:
        first = getattr(col, "First", None)
        if callable(first):
            it = first()
            while it is not None:
                items.append(it)
                nxt = getattr(col, "Next", None)
                it = nxt() if callable(nxt) else None
                if len(items) > 10000:
                    break
    except Exception:
        pass
    return items


def _edge_midpoint(edge: Any) -> Optional[Tuple[float, float, float]]:
    return None  # late-binding на v23 без typelib обычно не отдаёт; не блокируем


def _edge_direction(edge: Any) -> Optional[Tuple[float, float, float]]:
    return None


def collect_all_edges(part_com: Any) -> EdgeSet:
    """Собрать рёбра: EntityCollection(o3d_edge=7), иначе грани."""
    notes: List[str] = []

    col = _entity_collection(part_com, O3D_EDGE)
    if col is not None:
        raw_items = _iter_collection_items(col)
        notes.append(f"EntityCollection(7) count={len(raw_items)}")
        if raw_items:
            edges = [
                EdgeRef(com=it, index=i, source="EntityCollection(7)")
                for i, it in enumerate(raw_items)
            ]
            return EdgeSet(edges=edges, filter_name="all", _raw_collection=col)

    # через грани
    face_col = _entity_collection(part_com, O3D_FACE)
    found: List[EdgeRef] = []
    seen: set = set()
    if face_col is not None:
        faces = _iter_collection_items(face_col)
        notes.append(f"faces={len(faces)}")
        for fi, face in enumerate(faces):
            ecol = None
            for name in ("EdgeCollection", "GetEdgeCollection", "Edges"):
                try:
                    attr = getattr(face, name, None)
                    if attr is None:
                        continue
                    ecol = attr() if callable(attr) else attr
                    if ecol is not None:
                        break
                except Exception:
                    continue
            if ecol is None:
                continue
            for edge in _iter_collection_items(ecol):
                key = id(edge)
                if key in seen:
                    continue
                seen.add(key)
                found.append(
                    EdgeRef(com=edge, index=len(found), source=f"face[{fi}].edges")
                )

    if found:
        return EdgeSet(edges=found, filter_name="all")

    # диагностика: что реально отдают 6/7/8
    diag = []
    for tid, label in ((6, "face"), (7, "edge"), (8, "vertex")):
        c = _entity_collection(part_com, tid)
        n = _collection_count(c) if c is not None else None
        diag.append(f"{label}({tid})={n}")

    raise KompasOperationError(
        "Не удалось получить рёбра (o3d_edge=7). "
        f"Диагностика коллекций: {', '.join(diag)}. notes={notes}"
    )


def select_edges_near_point(
    part_com: Any,
    x: float,
    y: float,
    z: float,
) -> EdgeSet:
    """
    Канон API5: EntityCollection(7).SelectByPoint → First/Next.

    Example:
        edges = select_edges_near_point(part._part, 20, 0, 20)
    """
    col = _entity_collection(part_com, O3D_EDGE)
    if col is None:
        raise KompasOperationError("EntityCollection(o3d_edge=7) недоступна")

    try:
        # сброс селекции если есть
        for m in ("UnSelectAll", "Clear", "Refresh"):
            try:
                fn = getattr(col, m, None)
                if callable(fn):
                    fn()
            except Exception:
                pass
        sel = getattr(col, "SelectByPoint", None)
        if not callable(sel):
            raise KompasOperationError("SelectByPoint отсутствует на EntityCollection")
        sel(float(x), float(y), float(z))
    except KompasOperationError:
        raise
    except Exception as e:
        raise KompasOperationError(f"SelectByPoint({x},{y},{z}): {e}") from e

    items: List[Any] = []
    try:
        first = getattr(col, "First", None)
        if callable(first):
            it = first()
            while it is not None:
                items.append(it)
                nxt = getattr(col, "Next", None)
                it = nxt() if callable(nxt) else None
                if len(items) > 1000:
                    break
    except Exception as e:
        raise KompasOperationError(f"First/Next после SelectByPoint: {e}") from e

    if not items:
        # fallback: вся коллекция
        items = _iter_collection_items(col)

    if not items:
        raise KompasOperationError(
            f"SelectByPoint({x},{y},{z}): рёбер не найдено"
        )

    edges = [
        EdgeRef(com=it, index=i, source=f"SelectByPoint({x},{y},{z})")
        for i, it in enumerate(items)
    ]
    return EdgeSet(edges=edges, filter_name="near_point", _raw_collection=col)


def filter_edges(
    edge_set: EdgeSet,
    predicate: str,
    *,
    point: Optional[Tuple[float, float, float]] = None,
    tol: float = 1.0,
    part_com: Any = None,
) -> EdgeSet:
    pred = predicate.lower().strip()
    edges = list(edge_set.edges)

    if pred in ("all", "*", ""):
        return EdgeSet(
            edges=edges,
            filter_name="all",
            _raw_collection=edge_set._raw_collection,
        )

    if pred == "near_point":
        if point is None:
            raise KompasOperationError("near_point требует point=(x,y,z)")
        if part_com is not None:
            return select_edges_near_point(part_com, point[0], point[1], point[2])
        raise KompasOperationError(
            "near_point без part_com: используйте part.get_edges('near_point', point=...)"
        )

    # parallel_*/top_z требуют geometry — на late-binding обычно недоступны
    if pred.startswith("parallel_") or pred in ("top_z", "bottom_z"):
        raise KompasOperationError(
            f"filter {pred!r} на этой установке недоступен (нет midpoint/direction с COM). "
            "Используйте 'all' или near_point с SelectByPoint."
        )

    raise KompasOperationError(
        f"Неизвестный filter {predicate!r}. Доступно: all, near_point"
    )


def get_edges(
    part_com: Any,
    filter: str = "all",
    *,
    point: Optional[Tuple[float, float, float]] = None,
    tol: float = 1.0,
) -> EdgeSet:
    if filter.lower().strip() == "near_point":
        if point is None:
            raise KompasOperationError("near_point: укажите point=(x,y,z)")
        return select_edges_near_point(part_com, point[0], point[1], point[2])

    all_edges = collect_all_edges(part_com)
    return filter_edges(
        all_edges, filter, point=point, tol=tol, part_com=part_com
    )
