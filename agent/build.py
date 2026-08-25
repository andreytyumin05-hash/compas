"""
Сгенерировать код и выполнить в КОМПАС-3D.

  python -m agent.build "Втулка наружный 40 внутренний 20 длина 50"
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

from .code_fix import normalize_code, must_fix_holes
from .runner import Agent
from .validate import validate_generated_code

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def execute_code(code: str) -> None:
    code = normalize_code(code)
    namespace = {"__name__": "__kompas_script__"}
    exec(compile(code, "<agent-build>", "exec"), namespace, namespace)  # noqa: S102


def run_task(task: str) -> str:
    """Для CLI и Telegram: задача → код (уже проверенный) → exec. Возвращает код."""
    agent = Agent()
    code, errors = agent.generate_checked(task)
    if errors or must_fix_holes(code):
        raise RuntimeError(
            "Код не прошёл проверку: " + "; ".join(errors or ["отверстия без cut"])
        )
    ok, errors2 = validate_generated_code(code)
    if not ok:
        raise RuntimeError("Валидация: " + "; ".join(errors2))
    execute_code(code)
    return code


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
        execute_code(code)
        console.print("[green]Готово.[/]")
    except Exception as e:
        console.print(f"[red]Ошибка:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
