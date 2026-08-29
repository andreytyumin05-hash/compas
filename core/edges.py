"""
Выбор рёбер тела для фаски/скругления.

LLM и пользователь работают с предикатами, не с сырыми COM-ID:

    edges = part.get_edges("all")
    edges = part.get_edges("parallel_z")
    edges = part.get_edges("near_point", point=(0, 0, 25), tol=1.0)

Внутри — перебор коллекций рёбер/граней через late-bound COM API5.
Если конкретный фильтр на установке недоступен — понятный KompasOperationError.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Iterable, List, Optional, Sequence, Tuple, Union

from .exceptions import KompasOperationError

# Часто встречающиеся id в Obj3dType (могут отличаться — пробуем несколько)
_O3D_EDGE_CANDIDATES = (37, 36, 35, 8, 7)
_O3D_FACE_CANDIDATES = (6, 5, 4, 38)


@dataclass
class EdgeRef:
    """Одно ребро: COM-объект + метаданные для отладки."""

    com: Any
    index: int = -1
    source: str = ""
    midpoint: Optional[Tuple[float, float, float]] = None
    direction: Optional[Tuple[float, float, float]] = None  # unit, if known


@dataclass
class EdgeSet:
    """Набор рёбер — то, что принимают chamfer/fillet."""

    edges: List[EdgeRef] = field(default_factory=list)
    filter_name: str = ""

    def __len__(self) -> int:
        return len(self.edges)

    def __iter__(self):
        return iter(self.edges)

    def com_objects(self) -> List[Any]:
        return [e.com for e in self.edges if e.com is not None]


def _safe_call(obj: Any, name: str, *args):
    try:
        attr = getattr(obj, name)
    except Exception:
        return None
    try:
        if callable(attr):
            return attr(*args)
        return attr
    except Exception:
        return None


def _vec_len(v: Sequence[float]) -> float:
    return math.sqrt(sum(float(x) * float(x) for x in v))


def _normalize(v: Sequence[float]) -> Optional[Tuple[float, float, float]]:
    L = _vec_len(v)
    if L < 1e-12:
        return None
    return (float(v[0]) / L, float(v[1]) / L, float(v[2]) / L)


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return float(a[0]) * float(b[0]) + float(a[1]) * float(b[1]) + float(a[2]) * float(b[2])


def _edge_midpoint(edge: Any) -> Optional[Tuple[float, float, float]]:
    for method in ("GetEdgeParam", "GetParams", "GetMathPoint"):
        try:
            # разные сигнатуры SDK — best effort
            r = getattr(edge, method, None)
            if r is None:
                continue
            if callable(r):
                # иногда возвращает объект с x,y,z
                out = r()
            else:
                out = r
            if out is None:
                continue
            for attrs in (("x", "y", "z"), ("X", "Y", "Z")):
                try:
                    return (float(getattr(out, attrs[0])), float(getattr(out, attrs[1])), float(getattr(out, attrs[2])))
                except Exception:
                    pass
        except Exception:
            continue
    # Vertex endpoints average
    for a, b in (("Vertex1", "Vertex2"), ("GetVertex1", "GetVertex2")):
        try:
            v1 = getattr(edge, a)
            v2 = getattr(edge, b)
            if callable(v1):
                v1 = v1()
            if callable(v2):
                v2 = v2()
            p1 = _edge_midpoint(v1)  # reuse point reader if vertex looks similar
            # try Point property
            pts = []
            for v in (v1, v2):
                for attrs in (("x", "y", "z"), ("X", "Y", "Z")):
                    try:
                        pts.append(
                            (
                                float(getattr(v, attrs[0])),
                                float(getattr(v, attrs[1])),
                                float(getattr(v, attrs[2])),
                            )
                        )
                        break
                    except Exception:
                        continue
            if len(pts) == 2:
                return (
                    (pts[0][0] + pts[1][0]) / 2,
                    (pts[0][1] + pts[1][1]) / 2,
                    (pts[0][2] + pts[1][2]) / 2,
                )
        except Exception:
            continue
    return None


def _edge_direction(edge: Any) -> Optional[Tuple[float, float, float]]:
    for method in ("Direction", "GetDirection", "tangent"):
        try:
            d = getattr(edge, method, None)
            if d is None:
                continue
            if callable(d):
                d = d()
            for attrs in (("x", "y", "z"), ("X", "Y", "Z")):
                try:
                    return _normalize(
                        (
                            getattr(d, attrs[0]),
                            getattr(d, attrs[1]),
                            getattr(d, attrs[2]),
                        )
                    )
                except Exception:
                    pass
            if isinstance(d, (list, tuple)) and len(d) >= 3:
                return _normalize(d[:3])
        except Exception:
            continue
    return None


def _collect_from_entity_collection(part_com: Any) -> List[EdgeRef]:
    """part.EntityCollection(o3d_edge) — основной путь API5."""
    found: List[EdgeRef] = []
    errors = []
    for type_id in _O3D_EDGE_CANDIDATES:
        try:
            col = part_com.EntityCollection(type_id)
        except Exception as e:
            errors.append(f"EntityCollection({type_id}): {e}")
            continue
        if col is None:
            continue
        # Count / Item
        n = None
        for cname in ("Count", "GetCount", "count"):
            try:
                c = getattr(col, cname)
                n = int(c() if callable(c) else c)
                break
            except Exception:
                continue
        if n is None:
            # sometimes iterable
            try:
                for i, item in enumerate(col):
                    found.append(
                        EdgeRef(
                            com=item,
                            index=i,
                            source=f"EntityCollection({type_id})",
                            midpoint=_edge_midpoint(item),
                            direction=_edge_direction(item),
                        )
                    )
                if found:
                    return found
            except Exception as e:
                errors.append(f"iter col {type_id}: {e}")
            continue
        for i in range(1, n + 1):  # 1-based often
            item = None
            for iname, idx in (("Item", i), ("Item", i - 1), ("GetByIndex", i), ("GetByIndex", i - 1)):
                try:
                    fn = getattr(col, iname)
                    item = fn(idx) if callable(fn) else None
                    if item is not None:
                        break
                except Exception:
                    continue
            if item is None:
                continue
            found.append(
                EdgeRef(
                    com=item,
                    index=i,
                    source=f"EntityCollection({type_id})",
                    midpoint=_edge_midpoint(item),
                    direction=_edge_direction(item),
                )
            )
        if found:
            return found
    return found


def _collect_from_faces(part_com: Any) -> List[EdgeRef]:
    """Рёбра через грани: Face → EdgeCollection."""
    found: List[EdgeRef] = []
    seen = set()

    faces = []
    for type_id in _O3D_FACE_CANDIDATES:
        try:
            col = part_com.EntityCollection(type_id)
        except Exception:
            continue
        if col is None:
            continue
        n = None
        for cname in ("Count", "GetCount", "count"):
            try:
                c = getattr(col, cname)
                n = int(c() if callable(c) else c)
                break
            except Exception:
                continue
        if not n:
            continue
        for i in range(1, n + 1):
            face = None
            for iname, idx in (("Item", i), ("Item", i - 1)):
                try:
                    fn = getattr(col, iname)
                    face = fn(idx) if callable(fn) else None
                    if face is not None:
                        break
                except Exception:
                    continue
            if face is not None:
                faces.append(face)
        if faces:
            break

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
        n = None
        for cname in ("Count", "GetCount", "count"):
            try:
                c = getattr(ecol, cname)
                n = int(c() if callable(c) else c)
                break
            except Exception:
                continue
        if not n:
            continue
        for i in range(1, n + 1):
            edge = None
            for iname, idx in (("Item", i), ("Item", i - 1)):
                try:
                    fn = getattr(ecol, iname)
                    edge = fn(idx) if callable(fn) else None
                    if edge is not None:
                        break
                except Exception:
                    continue
            if edge is None:
                continue
            key = id(edge)
            if key in seen:
                continue
            seen.add(key)
            found.append(
                EdgeRef(
                    com=edge,
                    index=len(found),
                    source=f"face[{fi}].EdgeCollection",
                    midpoint=_edge_midpoint(edge),
                    direction=_edge_direction(edge),
                )
            )
    return found


def collect_all_edges(part_com: Any) -> EdgeSet:
    """Собрать все доступные рёбра тела."""
    edges = _collect_from_entity_collection(part_com)
    if not edges:
        edges = _collect_from_faces(part_com)
    if not edges:
        raise KompasOperationError(
            "Не удалось получить ни одного ребра через EntityCollection/Face.EdgeCollection. "
            "Типовая причина: unregistered typelib или тело ещё без solid (сначала extrude). "
            "Проверьте python -m core.smoke_edges после построения куба."
        )
    return EdgeSet(edges=edges, filter_name="all")


def filter_edges(
    edge_set: EdgeSet,
    predicate: str,
    *,
    point: Optional[Tuple[float, float, float]] = None,
    tol: float = 1.0,
    axis: str = "z",
) -> EdgeSet:
    """
    predicate:
      all — без фильтра
      parallel_x | parallel_y | parallel_z — |dir·axis| > 0.9
      near_point — midpoint в шаре tol вокруг point
      top_z — рёбра с максимальным z midpoint (верхний «пояс»)
      bottom_z — минимальный z
    """
    pred = predicate.lower().strip()
    edges = list(edge_set.edges)

    if pred in ("all", "*", ""):
        return EdgeSet(edges=edges, filter_name="all")

    if pred.startswith("parallel_"):
        axis = pred.split("_", 1)[1]
        axis_vec = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}.get(axis)
        if axis_vec is None:
            raise KompasOperationError(f"parallel_*: неизвестная ось {axis}")
        selected = []
        missing_dir = 0
        for e in edges:
            d = e.direction
            if d is None:
                missing_dir += 1
                continue
            if abs(_dot(d, axis_vec)) >= 0.9:
                selected.append(e)
        if not selected:
            raise KompasOperationError(
                f"filter parallel_{axis}: ни одного ребра с известным направлением. "
                f"(без direction: {missing_dir} из {len(edges)}). "
                "На этой установке метаданные ребра могут быть недоступны — используйте 'all'."
            )
        return EdgeSet(edges=selected, filter_name=pred)

    if pred == "near_point":
        if point is None:
            raise KompasOperationError("near_point требует point=(x,y,z)")
        selected = []
        for e in edges:
            m = e.midpoint
            if m is None:
                continue
            if _vec_len((m[0] - point[0], m[1] - point[1], m[2] - point[2])) <= tol:
                selected.append(e)
        if not selected:
            raise KompasOperationError(
                f"near_point: нет рёбер в tol={tol} от {point}. "
                "Часто midpoint не читается из COM — тогда только filter 'all'."
            )
        return EdgeSet(edges=selected, filter_name=pred)

    if pred in ("top_z", "bottom_z"):
        with_z = [(e, e.midpoint[2]) for e in edges if e.midpoint is not None]
        if not with_z:
            raise KompasOperationError(
                f"{pred}: нет рёбер с midpoint — COM не отдал координаты. Используйте 'all'."
            )
        zs = [z for _, z in with_z]
        target = max(zs) if pred == "top_z" else min(zs)
        selected = [e for e, z in with_z if abs(z - target) <= tol]
        return EdgeSet(edges=selected, filter_name=pred)

    raise KompasOperationError(
        f"Неизвестный filter {predicate!r}. "
        "Доступно: all, parallel_x/y/z, near_point, top_z, bottom_z"
    )


def get_edges(
    part_com: Any,
    filter: str = "all",
    *,
    point: Optional[Tuple[float, float, float]] = None,
    tol: float = 1.0,
) -> EdgeSet:
    """
    Собрать и отфильтровать рёбра.

    Example:
        edges = get_edges(part._part, "all")
        edges = get_edges(part._part, "parallel_z")
        edges = get_edges(part._part, "near_point", point=(0,0,10), tol=2)
    """
    all_edges = collect_all_edges(part_com)
    return filter_edges(all_edges, filter, point=point, tol=tol)
