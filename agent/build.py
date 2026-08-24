"""
Сгенерировать код и сразу выполнить в КОМПАС-3D.

  python -m agent.build "Втулка: наружный 40, внутренний 20, длина 50"

КОМПАС должен быть запущен (или будет запущен через COM).
"""

from __future__ import annotations

import sys
from pathlib import Path

from rich.console import Console
from rich.syntax import Syntax

from .runner import Agent
from .validate import validate_generated_code

# корень проекта в sys.path для `from core import Part`
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def execute_code(code: str) -> None:
    """Исполнить код в изолированном namespace с доступом к core."""
    namespace = {"__name__": "__kompas_script__"}
    exec(compile(code, "<agent-build>", "exec"), namespace, namespace)  # noqa: S102


def main() -> None:
    console = Console()

    if len(sys.argv) < 2:
        console.print('[yellow]Использование:[/] python -m agent.build "описание детали"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    console.print(f"[bold]Задача:[/] {task}\n")

    try:
        agent = Agent()
        code = agent.generate(task)
        console.print("[green]Код:[/]\n")
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))

        ok, errors = validate_generated_code(code)
        if not ok:
            console.print("\n[red]Код не прошёл проверку API — запуск отменён:[/]")
            for e in errors:
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
