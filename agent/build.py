"""
Сгенерировать код и выполнить в КОМПАС-3D (с retry при ошибке COM).

  python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
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
    """
    Задача → код → exec. При ошибке КОМПАС — до max_com_retries исправлений LLM.
    Возвращает финальный код.
    """
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
            # попросить LLM исправить с учётом runtime-ошибки
            repair = build_repair_prompt(task, code, [str(e)])
            raw = agent.llm.chat(
                [
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": repair},
                ],
                temperature=0.1,
            )
            code = normalize_code(agent._extract_code(raw))
            ok, errs = validate_generated_code(code)
            if not ok:
                raise RuntimeError(
                    f"После ошибки COM код снова невалиден: {errs}; COM: {e}"
                ) from e

    raise RuntimeError(f"КОМПАС не построил за {max_com_retries} попыток: {last_err}")


def run_task_export(
    task: str,
    out_path: str | Path,
    fmt: str = "step",
) -> Tuple[str, Path]:
    """Построить и экспортировать. Возвращает (code, path)."""
    from core import Part  # noqa: F401 — доступно в exec namespace indirectly

    code = run_task(task)
    # повторный exec с захватом part — хрупко; проще попросить код сохранить
    # Практичный путь: exec + Part.from_active().export
    from core import Part

    p = Part.from_active()
    path = p.export(out_path, fmt=fmt)
    return code, path


def main() -> None:
    console = Console()

    if len(sys.argv) < 2:
        console.print('[yellow]Использование:[/] python -m agent.build "описание детали"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    console.print(f"[bold]Задача:[/] {task}\n")

    try:
        agent = Agent()
        code, errors = agent.generate_checked(task)
        console.print("[green]Код:[/]\n")
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))

        if errors or must_fix_holes(code):
            console.print("\n[red]Код не прошёл проверку — запуск отменён:[/]")
            for e in errors or ["нужен part.cut для отверстий"]:
                console.print(f"  • {e}")
            sys.exit(2)

        console.print("\n[cyan]Запуск в КОМПАС…[/]")
        # с retry
        final = run_task(task)
        if final != code:
            console.print("[yellow]Код был исправлен после ошибки COM.[/]")
            console.print(Syntax(final, "python", theme="monokai", line_numbers=True))
        console.print("[green]Готово.[/]")
    except Exception as e:
        console.print(f"[red]Ошибка:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
