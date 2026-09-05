"""CLI bridge used by the KOMPAS ActiveX add-in.

The native add-in owns only UI/lifecycle. This process reuses the existing Python
agent and core so there is exactly one CAD implementation. Internal Python logs
are deliberately suppressed: the UI receives only a compact machine-readable
result.
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
    return Path(path).read_text(encoding="utf-8").strip()


def _create(task: str, *, mode: str = "create") -> Path:
    from agent.build import run_task_export
    from core.model_store import latest_model_path
    _, out = run_task_export(task, latest_model_path(), fmt="m3d", mode=mode)
    return Path(out)


def _save() -> Path:
    from core import Part
    from core.model_store import latest_model_path, store_latest_model
    part = Part.from_active()
    out = latest_model_path()
    exported = part.export(out, fmt="m3d")
    return store_latest_model(exported)


def _run_quiet(fn):
    stdout = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        return fn()


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("action", choices=("create", "edit", "save"))
    parser.add_argument("--task-file", default="")
    args = parser.parse_args()

    try:
        if args.action == "save":
            result = _run_quiet(_save)
        else:
            if not args.task_file:
                raise ValueError("--task-file is required")
            task = _task_from_file(args.task_file)
            if not task:
                raise ValueError("empty task")
            if args.action == "edit":
                task = (
                    "EDIT REQUEST. Use the currently open KOMPAS detail as the source of truth. "
                    "Preserve all existing features, named parameters and relations unless this request explicitly changes them. "
                    "Do not create a new document. Return a complete replacement edit script operating on the active document.\n\n"
                    + task
                )
                result = _run_quiet(lambda: _create(task, mode="edit"))
            else:
                result = _run_quiet(lambda: _create(task, mode="create"))
        print(json.dumps({"ok": True, "path": str(result)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
