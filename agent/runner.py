"""Генерация кода: python -m agent.runner "описание"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .code_fix import normalize_code, must_fix_holes, semantic_warnings
from .llm import get_llm_client, BaseLLM
from .prompts import SYSTEM_PROMPT, build_user_prompt, build_repair_prompt
from .validate import validate_generated_code


class Agent:
    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or get_llm_client()

    def generate(self, task: str, temperature: float = 0.15) -> str:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        raw = self.llm.chat(messages, temperature=temperature)
        return normalize_code(self._extract_code(raw))

    def generate_checked(
        self, task: str, temperature: float = 0.15, max_retries: int = 2
    ) -> Tuple[str, List[str]]:
        """Код + ошибки. При провале валидации/дырках — 1–2 retry с repair-промптом."""
        code = self.generate(task, temperature=temperature)
        ok, errors = validate_generated_code(code)
        if ok and must_fix_holes(code):
            ok = False
            errors = list(errors) + [
                "отверстия нарисованы, но нет part.cut(..., through_all=True)"
            ]

        attempt = 0
        while (not ok or must_fix_holes(code)) and attempt < max_retries:
            attempt += 1
            repair_msgs = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_repair_prompt(task, code, errors),
                },
            ]
            raw = self.llm.chat(repair_msgs, temperature=0.1)
            code = normalize_code(self._extract_code(raw))
            ok, errors = validate_generated_code(code)
            if ok and must_fix_holes(code):
                ok = False
                errors = [
                    "отверстия нарисованы, но нет part.cut(..., through_all=True)"
                ]

        if ok:
            # мягкие предупреждения не блокируют
            return code, []
        return code, errors

    def generate_raw(self, task: str, temperature: float = 0.15) -> str:
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
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    console.print(f"[bold]Задача:[/] {task}\n")

    try:
        agent = Agent()
        code, errors = agent.generate_checked(task)
        console.print("[green]Сгенерированный код:[/]\n")
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        warns = semantic_warnings(code)
        if errors:
            console.print("\n[red]Статическая проверка не пройдена:[/]")
            for e in errors:
                console.print(f"  • {e}")
            sys.exit(2)
        if warns:
            console.print("\n[yellow]Замечания:[/]")
            for w in warns:
                console.print(f"  • {w}")
        console.print("\n[green]Статическая проверка: OK[/]")
    except Exception as e:
        console.print(f"[red]Ошибка:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
