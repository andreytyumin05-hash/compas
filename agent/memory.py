"""Local memory: keep one latest CAD build context, discard older contexts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List

_ROOT = Path(__file__).resolve().parent.parent
_LATEST = _ROOT / ".compas_tmp" / "latest_context.json"

_EDIT_WORDS = (
    "измени", "изменить", "передел", "исправь", "исправить", "поменяй", "поменять",
    "замени", "заменить", "сделай вместо", "вместо", "добавь", "добавить", "убери",
    "убрать", "удали", "удалить", "доработ", "перемести", "перенеси", "смести",
    "увелич", "увеличь", "уменьш", "уменьши", "пересчитай", "пересчитать",
    "эту деталь", "предыдущ", "последн", "старую модель", "текущую модель",
)


def _norm(task: str) -> str:
    t = (task or "").lower()
    t = re.sub(r"\d+(?:\.\d+)?", "#", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:300]


def remember(task: str, code: str, *, tree: str = "", engineering: str = "") -> None:
    if not code or "Part.create" not in code:
        return
    _LATEST.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "task_norm": _norm(task),
        "task": task[:4000],
        "code": code[:14000],
        "tree": tree[:8000],
        "engineering": engineering[:6000],
    }
    _LATEST.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _load() -> dict:
    try:
        row = json.loads(_LATEST.read_text(encoding="utf-8"))
        return row if isinstance(row, dict) else {}
    except Exception:
        return {}


def recall(task: str, limit: int = 1) -> List[str]:
    if limit < 1 or not _LATEST.is_file():
        return []
    row = _load()
    code = str(row.get("code") or "")
    return [code] if code else []


def latest_edit_context(task: str) -> str:
    t = (task or "").lower()
    if not any(word in t for word in _EDIT_WORDS):
        return ""
    row = _load()
    if not row:
        return ""
    parts = [
        "LATEST MODEL = current source of truth for this edit.",
        f"LATEST TASK:\n{str(row.get('task') or '')[:4000]}",
        f"LATEST GENERATED SCRIPT:\n```python\n{str(row.get('code') or '')[:14000]}\n```",
    ]
    tree = str(row.get("tree") or "").strip()
    if tree:
        parts.append("LATEST FEATURE TREE:\n" + tree[:8000])
    engineering = str(row.get("engineering") or "").strip()
    if engineering:
        parts.append("LATEST ENGINEERING CONTEXT:\n" + engineering[:5000])
    return "\n\n".join(parts)


def few_shot_from_memory(task: str) -> str:
    t = (task or "").lower()
    if not any(word in t for word in _EDIT_WORDS):
        return ""
    codes = recall(task, limit=1)
    if not codes:
        return ""
    return "### Latest successful model script\n```python\n" + codes[0] + "\n```"
