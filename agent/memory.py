"""Local memory for successful CAD builds and the latest editable context."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

_ROOT = Path(__file__).resolve().parent.parent
_MEM = _ROOT / ".compas_tmp" / "build_memory.jsonl"
_LATEST = _ROOT / ".compas_tmp" / "latest_context.json"
_MAX = 40


def _norm(task: str) -> str:
    t = (task or "").lower()
    t = re.sub(r"\d+(?:\.\d+)?", "#", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:200]


def remember(task: str, code: str) -> None:
    if not code or "Part.create" not in code:
        return
    _MEM.parent.mkdir(parents=True, exist_ok=True)
    row = {"task_norm": _norm(task), "task": task[:500], "code": code[:12000]}
    with _MEM.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    # Keep exactly one latest build context for follow-up edit requests.
    _LATEST.write_text(
        json.dumps({"task": task[:4000], "code": code[:12000]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def recall(task: str, limit: int = 2) -> List[str]:
    if not _MEM.is_file():
        return []
    key = _norm(task)
    hits: List[str] = []
    try:
        lines = _MEM.read_text(encoding="utf-8").splitlines()[-_MAX:]
        for line in reversed(lines):
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            norm = row.get("task_norm") or ""
            if norm == key or (key and key[:40] in norm):
                code = row.get("code") or ""
                if code:
                    hits.append(code)
                if len(hits) >= limit:
                    break
    except Exception:
        return []
    return hits


def latest_edit_context(task: str) -> str:
    """Return only the latest model context when the user is asking to edit it."""
    t = (task or "").lower()
    edit_words = (
        "измени", "изменить", "передел", "добавь", "убери", "убрать", "исправь",
        "доработ", "сделай отверстие", "перемести", "увелич", "уменьш", "эту деталь",
        "предыдущ", "старую модель", "последнюю модель",
    )
    if not any(word in t for word in edit_words):
        return ""
    try:
        if not _LATEST.is_file():
            return ""
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
    codes = recall(task)
    if not codes:
        return ""
    blocks = []
    for i, code in enumerate(codes, 1):
        blocks.append(f"### Успешный пример {i}\n```python\n{code}\n```")
    return "\n\n".join(blocks)
