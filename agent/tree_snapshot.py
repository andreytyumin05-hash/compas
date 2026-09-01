"""Снимок дерева построения / контекста для repair-промпта (best-effort)."""

from __future__ import annotations

from typing import Any, List


def snapshot_feature_tree(part: Any, *, max_items: int = 40) -> str:
    """Текст для LLM: что уже в модели."""
    lines: List[str] = []
    com = getattr(part, "_part", None) or part
    # API7-style
    for attr in ("FeatureTree", "Tree", "EntityCollection", "Operations"):
        try:
            tree = getattr(com, attr, None)
            tree = tree() if callable(tree) else tree
            if tree is None:
                continue
            count = getattr(tree, "Count", None) or getattr(tree, "count", None)
            if callable(count):
                count = count()
            if not count:
                continue
            n = int(count)
            lines.append(f"{attr}: {n} элементов")
            for i in range(min(n, max_items)):
                try:
                    item = tree.Item(i) if hasattr(tree, "Item") else tree[i]
                    name = (
                        getattr(item, "name", None)
                        or getattr(item, "Name", None)
                        or getattr(item, "typeName", None)
                        or type(item).__name__
                    )
                    lines.append(f"  [{i}] {name}")
                except Exception:
                    continue
            break
        except Exception:
            continue

    try:
        ctx = part.get_context()
        if ctx:
            lines.append("session_context: " + str(list(ctx.keys())[:12]))
            if "variables" in ctx:
                lines.append("vars: " + str(ctx.get("variables"))[:200])
    except Exception:
        pass

    if not lines:
        return "(дерево недоступно через COM — только код)"
    return "\n".join(lines)
