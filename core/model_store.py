"""Persistent single-model storage for the local KOMPAS session.

The latest native .m3d is retained; older stored copies are replaced. Telegram
session directories remain disposable.
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any, Dict

_ROOT = Path(os.environ.get("COMPAS_TMP", Path.cwd() / ".compas_tmp"))
_LATEST = _ROOT / "latest_model.m3d"
_META = _ROOT / "latest_model.json"


def latest_model_path() -> Path:
    return _LATEST


def has_latest_model() -> bool:
    return _LATEST.is_file() and _LATEST.stat().st_size > 0


def store_latest_model(path: str | Path, *, task: str = "", code: str = "") -> Path:
    source = Path(path)
    if not source.is_file() or source.stat().st_size <= 0:
        raise FileNotFoundError(f"M3D source does not exist: {source}")
    _ROOT.mkdir(parents=True, exist_ok=True)
    temp = _LATEST.with_suffix(".tmp.m3d")
    shutil.copy2(source, temp)
    temp.replace(_LATEST)
    metadata: Dict[str, Any] = {
        "model": str(_LATEST),
        "task": (task or "")[:2000],
        "code": (code or "")[:12000],
    }
    _META.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    return _LATEST


def latest_metadata() -> Dict[str, Any]:
    try:
        if _META.is_file():
            value = json.loads(_META.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
    except Exception:
        pass
    return {}


def clear_latest_model() -> None:
    for path in (_LATEST, _META):
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
