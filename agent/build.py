"""
Сгенерировать код и выполнить в КОМПАС-3D (retry при ошибке COM).

  python -m agent.build "описание"
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional, Tuple

from rich.console import Console
from rich.syntax import Syntax

from .code_fix import normalize_code, must_fix_holes
from .prompts import build_repair_prompt, get_system_prompt
from .runner import Agent
from .validate import validate_generated_code

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def execute_code(code: str) -> None:
    code = normalize_code(code)
    namespace = {"__name__": "__kompas_script__"}
    exec(compile(code, "<agent-build>", "exec"), namespace, namespace)  # noqa: S102


def run_task(task: str, *, max_com_retries: int = 3) -> str:
    """Задача → один generate_checked → exec; при COM-ошибке — repair LLM."""
    agent = Agent()
    code, errors = agent.generate_checked(task)
    if errors or must_fix_holes(code):
        raise RuntimeError(
            "Код не прошёл проверку: " + "; ".join(errors or ["отверстия без cut"])
        )
    ok, errors2 = validate_generated_code(code)
    if not ok:
        raise RuntimeError("Валидация: " + "; ".join(errors2))

    last_err: Optional[BaseException] = None
    for attempt in range(max_com_retries):
        try:
            execute_code(code)
            return code
        except Exception as e:
            last_err = e
            if attempt + 1 >= max_com_retries:
                break
            repair = build_repair_prompt(task, code, [str(e)])
            raw = agent.llm.chat(
                [
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": repair},
                ],
                temperature=0.1,
            )
            new_code = normalize_code(agent._extract_code(raw or ""))
            ok, errs = validate_generated_code(new_code)
            if not ok:
                # не затираем рабочую попытку мусором
                continue
            code = new_code

    raise RuntimeError(f"КОМПАС не построил за {max_com_retries} попыток: {last_err}")


def run_task_export(
    task: str,
    out_path: str | Path,
    fmt: str = "m3d",
) -> Tuple[str, Path]:
    from core import Part

    code = run_task(task)
    p = Part.from_active()
    path = p.export(out_path, fmt=fmt)
    return code, path


def main() -> None:
    console = Console()
    if len(sys.argv) < 2:
        console.print('[yellow]Использование:[/] python -m agent.build "описание"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    console.print(f"[bold]Задача:[/] {task}\n")

    try:
        agent = Agent()
        code, errors = agent.generate_checked(task)
        if code:
            console.print("[green]Код:[/]\n")
            console.print(Syntax(code, "python", theme="monokai", line_numbers=True))

        if errors or must_fix_holes(code):
            console.print("\n[red]Проверка не пройдена:[/]")
            for e in errors or ["отверстия без cut"]:
                console.print(f"  • {e}")
            sys.exit(2)

        console.print("\n[cyan]Запуск в КОМПАС…[/]")
        last_err = None
        final = code
        for attempt in range(3):
            try:
                execute_code(final)
                if final != code:
                    console.print("[yellow]Код после COM-repair:[/]")
                    console.print(
                        Syntax(final, "python", theme="monokai", line_numbers=True)
                    )
                console.print("[green]Готово.[/]")
                return
            except Exception as e:
                last_err = e
                console.print(f"[yellow]COM attempt {attempt+1}: {e}[/]")
                repair = build_repair_prompt(task, final, [str(e)])
                raw = agent.llm.chat(
                    [
                        {"role": "system", "content": get_system_prompt()},
                        {"role": "user", "content": repair},
                    ],
                    temperature=0.1,
                )
                new_code = normalize_code(agent._extract_code(raw or ""))
                ok, errs = validate_generated_code(new_code)
                if ok:
                    final = new_code
                else:
                    console.print(f"[dim]repair отклонён: {errs}[/]")
        console.print(f"[red]Ошибка:[/] {last_err}")
        sys.exit(1)
    except Exception as e:
        console.print(f"[red]Ошибка:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
