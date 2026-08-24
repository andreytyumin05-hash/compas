"""
Запуск агента: задача → код для КОМПАС-3D.
"""

from __future__ import annotations

import re
from typing import Optional

from .llm import get_llm_client, BaseLLM
from .prompts import SYSTEM_PROMPT, build_user_prompt


class Agent:
    """
    Простой агент генерации кода под обёртку core.

    Позже можно расширить до ReAct-цикла с инструментами.
    """

    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or get_llm_client()

    def generate(self, task: str, temperature: float = 0.2) -> str:
        """
        Сгенерировать Python-код по текстовому описанию детали.

        Возвращает чистый код (без markdown-обёртки).
        """
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        raw = self.llm.chat(messages, temperature=temperature)
        return self._extract_code(raw)

    def generate_raw(self, task: str, temperature: float = 0.2) -> str:
        """Вернуть полный ответ модели (с пояснениями)."""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        return self.llm.chat(messages, temperature=temperature)

    @staticmethod
    def _extract_code(text: str) -> str:
        """Вытащить код из markdown-блока, если он есть."""
        pattern = r"```(?:python)?\s*([\s\S]*?)```"
        matches = re.findall(pattern, text)
        if matches:
            return matches[-1].strip()
        return text.strip()


def main():
    """CLI: python -m agent.runner \"сделай втулку...\""""
    import sys
    from rich.console import Console
    from rich.syntax import Syntax

    console = Console()

    if len(sys.argv) < 2:
        console.print("[yellow]Использование:[/] python -m agent.runner \"описание детали\"")
        console.print('Пример: python -m agent.runner "Втулка: внешний Ø40, внутренний Ø20, длина 50"')
        sys.exit(1)

    task = " ".join(sys.argv[1:])
    console.print(f"[bold]Задача:[/] {task}\n")

    try:
        agent = Agent()
        code = agent.generate(task)
        console.print("[green]Сгенерированный код:[/]\n")
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
    except Exception as e:
        console.print(f"[red]Ошибка:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
