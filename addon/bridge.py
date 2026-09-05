"""Minimal CLI bridge for the KOMPAS Add-In.

All internal Python stdout/stderr is suppressed. The parent UI receives one
compact JSON line only. Edit uses a dedicated active-document path.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _task_from_file(path: str) -> str:
    value = Path(path).read_text(encoding="utf-8").strip()
    if not value:
        raise ValueError("empty task")
    return value


def _run_create(task: str) -> Path:
    from agent.build import run_task_export
    from core.model_store import latest_model_path
    _, out = run_task_export(task, latest_model_path(), fmt="m3d", mode="create")
    return Path(out)


def _run_edit(task: str) -> Path:
    from agent.build import run_edit_open_document
    from core.model_store import latest_model_path
    _, out = run_edit_open_document(task, latest_model_path())
    if out is None:
        raise RuntimeError("edit не вернул сохранённую модель")
    return Path(out)


def _run_save() -> Path:
    from core import Part
    from core.model_store import latest_model_path, store_latest_model
    part = Part.from_active()
    exported = part.export(latest_model_path(), fmt="m3d")
    return store_latest_model(exported)


def _quiet(fn):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn()


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("action", choices=("create", "edit", "save"))
    parser.add_argument("--task-file", default="")
    args = parser.parse_args()
    try:
        if args.action == "save":
            result = _quiet(_run_save)
        else:
            task = _task_from_file(args.task_file)
            if args.action == "edit":
                result = _quiet(lambda: _run_edit(task))
            else:
                result = _quiet(lambda: _run_create(task))
        print(json.dumps({"ok": True, "path": str(result)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
