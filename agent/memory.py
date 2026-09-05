"""Local memory: keep one latest CAD build context, discard older contexts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

_ROOT = Path(__file__).resolve().parent.parent
_LATEST = _ROOT / ".compas_tmp" / "latest_context.json"


def _norm(task: str) -> str:
    t = (task or "").lower()
    t = re.sub(r"\d+(?:\.\d+)?", "#", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:300]


def remember(task: str, code: str) -> None:
    if not code or "Part.create" not in code:
        return
    _LATEST.parent.mkdir(parents=True, exist_ok=True)
    _LATEST.write_text(
        json.dumps(
            {"task_norm": _norm(task), "task": task[:4000], "code": code[:12000]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def recall(task: str, limit: int = 1) -> List[str]:
    if limit < 1 or not _LATEST.is_file():
        return []
    try:
        row = json.loads(_LATEST.read_text(encoding="utf-8"))
        if not isinstance(row, dict):
            return []
        code = str(row.get("code") or "")
        if not code:
            return []
        query = _norm(task)
        stored = str(row.get("task_norm") or "")
        # Similarity is intentionally conservative: a follow-up edit may have
        # different dimensions, but should still be able to reuse the latest model.
        if query and stored and (query == stored or any(token in stored for token in query.split()[:3])):
            return [code]
    except Exception:
        return []
    return []


def latest_edit_context(task: str) -> str:
    t = (task or "").lower()
    edit_words = (
        "измени", "изменить", "передел", "добавь", "убери", "убрать", "исправь",
        "доработ", "перемести", "увелич", "уменьш", "эту деталь", "предыдущ",
        "последн", "старую модель",
    )
    if not any(word in t for word in edit_words):
        return ""
    try:
        row = json.loads(_LATEST.read_text(encoding="utf-8"))
        if not isinstance(row, dict):
            return ""
        return (
            f"LATEST TASK:\n{str(row.get('task') or '')[:4000]}\n\n"
            f"LATEST GENERATED SCRIPT:\n```python\n{str(row.get('code') or '')[:12000]}\n```"
        )
    except Exception:
        return ""


def few_shot_from_memory(task: str) -> str:
    codes = recall(task, limit=1)
    if not codes:
        return ""
    return "### Latest successful example\n```python\n" + codes[0] + "\n```"
