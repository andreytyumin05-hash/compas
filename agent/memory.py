"""
Память удачных построений (локальный файл, не git).

После успешного build — сохранить сниппет; при похожей задаче — подсказать LLM.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import List, Optional

_ROOT = Path(__file__).resolve().parent.parent
_MEM = _ROOT / ".compas_tmp" / "build_memory.jsonl"
_MAX = 40


def _norm(task: str) -> str:
    t = task.lower()
    t = re.sub(r"\d+(?:\.\d+)?", "#", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t[:200]


def remember(task: str, code: str) -> None:
    if not code or "Part.create" not in code:
        return
    _MEM.parent.mkdir(parents=True, exist_ok=True)
    row = {"task_norm": _norm(task), "task": task[:300], "code": code[:4000]}
    with _MEM.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


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
            if row.get("task_norm") == key or (
                key and key[:40] in (row.get("task_norm") or "")
            ):
                c = row.get("code") or ""
                if c:
                    hits.append(c)
                if len(hits) >= limit:
                    break
    except Exception:
        return []
    return hits


def few_shot_from_memory(task: str) -> str:
    codes = recall(task)
    if not codes:
        return ""
    blocks = []
    for i, c in enumerate(codes, 1):
        blocks.append(f"### Успешный пример {i}\n```python\n{c}\n```")
    return "\n\n".join(blocks)
