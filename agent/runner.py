"""
Генерация кода: python -m agent.runner "описание детали"
"""

from __future__ import annotations

import re
from typing import Optional

from .llm import get_llm_client, BaseLLM
from .prompts import SYSTEM_PROMPT, build_user_prompt
from .validate import validate_generated_code


class Agent:
    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or get_llm_client()

    def generate(self, task: str, temperature: float = 0.2) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        raw = self.llm.chat(messages, temperature=temperature)
        return self._extract_code(raw)

    def generate_checked(self, task: str, temperature: float = 0.2) -> tuple[str, list[str]]:
        """Код + список ошибок валидации (пустой список = ок)."""
        code = self.generate(task, temperature=temperature)
        ok, errors = validate_generated_code(code)
        return code, ([] if ok else errors)

    def generate_raw(self, task: str, temperature: float = 0.2) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        return self.llm.chat(messages, temperature=temperature)

    @staticmethod
    def _extract_code(text: str) -> str:
        pattern = r"```(?:python)?\s*([\s\S]*?)```"
        matches = re.findall(pattern, text)
        if matches:
            return matches[-1].strip()
        return text.strip()


def main() -> None:
    import sys
    from rich.console import Console
    from rich.syntax import Syntax

    console = Console()

    if len(sys.argv) < 2:
        console.print('[yellow]Использование:[/] python -m agent.runner "описание детали"')
        console.print('Пример: python -m agent.runner "Фланец Ø80, толщина 10, 4 отверстия Ø9 на диаметре 60"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    console.print(f"[bold]Задача:[/] {task}\n")

    try:
        agent = Agent()
        code, errors = agent.generate_checked(task)
        console.print("[green]Сгенерированный код:[/]\n")
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        if errors:
            console.print("\n[red]Проверка API не пройдена:[/]")
            for e in errors:
                console.print(f"  • {e}")
            console.print("[yellow]Код лучше не запускать в КОМПАСе без правки.[/]")
            sys.exit(2)
        else:
            console.print("\n[green]Проверка API: OK[/]")
    except Exception as e:
        console.print(f"[red]Ошибка:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
