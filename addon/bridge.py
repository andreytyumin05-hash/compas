"""CLI bridge used by the KOMPAS ActiveX add-in.

The native add-in owns only UI/lifecycle. This process reuses the existing Python
agent and core so there is exactly one CAD implementation.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _task_from_file(path: str) -> str:
    p = Path(path)
    return p.read_text(encoding="utf-8").strip()


def _create(task: str) -> Path:
    from agent.build import run_task_export
    from core.model_store import latest_model_path

    _, out = run_task_export(task, latest_model_path(), fmt="m3d")
    return Path(out)


def _save() -> Path:
    from core import Part
    from core.model_store import latest_model_path, store_latest_model

    part = Part.from_active()
    # Exporting through the existing core keeps the save semantics identical to
    # Telegram/desktop builds and guarantees that only the latest .m3d is retained.
    out = latest_model_path()
    exported = part.export(out, fmt="m3d")
    return store_latest_model(exported)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("create", "edit", "save"))
    parser.add_argument("--task-file", default="")
    args = parser.parse_args()

    try:
        if args.action == "save":
            result = _save()
        else:
            if not args.task_file:
                raise ValueError("--task-file is required")
            task = _task_from_file(args.task_file)
            if not task:
                raise ValueError("empty task")
            if args.action == "edit":
                task = "Измени последнюю модель. Сохрани существующую конструктивную логику и параметры, меняй только то, что явно указано ниже.\n\n" + task
            result = _create(task)
        print(json.dumps({"ok": True, "path": str(result)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
