"""Сборка в КОМПАС + память успехов."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.syntax import Syntax

from .code_fix import normalize_code, must_fix_holes, check_task_feature_requirements
from .memory import remember
from .prompts import build_repair_prompt, get_system_prompt
from .runner import Agent
from .validate import validate_generated_code

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def execute_code(code: str) -> None:
    code = normalize_code(code)
    ns = {"__name__": "__kompas_script__"}
    exec(compile(code, "<agent-build>", "exec"), ns, ns)  # noqa: S102


def run_task(task: str, *, max_com_retries: int = 2) -> str:
    agent = Agent()
    code, errors = agent.generate_checked(task)
    missing = check_task_feature_requirements(task, code)
    if errors or must_fix_holes(code) or missing:
        raise RuntimeError(
            "Код не прошёл проверку: "
            + "; ".join((errors or []) + (["не хватает фич из ТЗ: " + ", ".join(missing)] if missing else []) + (["отверстия без cut"] if must_fix_holes(code) else []))
        )

    last_err: Optional[BaseException] = None
    final = code
    for attempt in range(max_com_retries):
        try:
            execute_code(final)
            remember(task, final)
            return final
        except Exception as e:
            last_err = e
            if attempt + 1 >= max_com_retries:
                break
            try:
                raw = agent.llm.chat(
                    [
                        {"role": "system", "content": get_system_prompt(task)},
                        {
                            "role": "user",
                            "content": build_repair_prompt(task, final, [str(e)]),
                        },
                    ],
                    temperature=0.1,
                )
                new_code = normalize_code(agent._extract_code(raw or ""))
                ok, _ = validate_generated_code(new_code)
                if ok:
                    final = new_code
            except Exception:
                pass
    raise RuntimeError(f"КОМПАС: {last_err}")


def run_task_export(
    task: str, out_path: str | Path, fmt: str = "m3d"
) -> Tuple[str, Path]:
    from core import Part

    code = run_task(task)
    path = Part.from_active().export(out_path, fmt=fmt)
    return code, path


def main() -> None:
    console = Console()
    if len(sys.argv) < 2:
        console.print('[yellow]python -m agent.build "описание"[/]')
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    try:
        code = run_task(task)
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        console.print("[green]Готово.[/]")
    except Exception as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
