"""Генерация кода: python -m agent.runner "описание"""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .code_fix import normalize_code, must_fix_holes, semantic_warnings
from .llm import get_llm_client, BaseLLM
from .prompts import get_system_prompt, build_user_prompt, build_repair_prompt
from .validate import validate_generated_code


class Agent:
    def __init__(self, llm: Optional[BaseLLM] = None):
        self.llm = llm or get_llm_client()

    def generate(self, task: str, temperature: float = 0.15) -> str:
        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        raw = self.llm.chat(messages, temperature=temperature)
        return normalize_code(self._extract_code(raw))

    def generate_checked(
        self, task: str, temperature: float = 0.15, max_retries: int = 3
    ) -> Tuple[str, List[str]]:
        last_raw = ""
        code = ""
        errors: List[str] = ["пустой код"]

        for attempt in range(max_retries + 1):
            if attempt == 0:
                messages = [
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": build_user_prompt(task)},
                ]
                temp = temperature
            elif not code.strip():
                messages = [
                    {"role": "system", "content": get_system_prompt()},
                    {
                        "role": "user",
                        "content": (
                            build_user_prompt(task)
                            + "\n\nКРИТИЧНО: предыдущий ответ был пустым или без кода. "
                            "Ответь ТОЛЬКО одним блоком:\n```python\nfrom core import Part\n...\n```\n"
                            "Без рассуждений до и после блока."
                        ),
                    },
                ]
                temp = 0.1
            else:
                messages = [
                    {"role": "system", "content": get_system_prompt()},
                    {
                        "role": "user",
                        "content": build_repair_prompt(task, code, errors),
                    },
                ]
                temp = 0.1

            last_raw = self.llm.chat(messages, temperature=temp) or ""
            code = normalize_code(self._extract_code(last_raw))
            ok, errors = validate_generated_code(code)
            if ok and must_fix_holes(code):
                ok = False
                errors = list(errors) + [
                    "отверстия нарисованы, но нет part.cut / hole"
                ]
            if ok:
                return code, []

        if not code.strip():
            preview = (last_raw or "")[:400].replace("\n", " ")
            return "", [
                "пустой код — модель не вернула Python. "
                f"Фрагмент ответа LLM: {preview!r}. "
                "Проверь LLM_MODEL на Groq (list_models) или смени модель."
            ]
        return code, errors

    def generate_raw(self, task: str, temperature: float = 0.15) -> str:
        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        return self.llm.chat(messages, temperature=temperature)

    @staticmethod
    def _extract_code(text: str) -> str:
        if not text or not str(text).strip():
            return ""
        text = str(text)

        # убрать think-блоки (некоторые модели)
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
        text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", text, flags=re.I)

        pattern = r"```(?:python)?\s*([\s\S]*?)```"
        matches = re.findall(pattern, text, flags=re.I)
        if matches:
            # последний python-блок, предпочтительно с Part
            for block in reversed(matches):
                if "Part" in block or "from core" in block:
                    return block.strip()
            return matches[-1].strip()

        # без markdown: от from core import Part до конца
        m = re.search(
            r"(from\s+core\s+import\s+Part[\s\S]+)", text, flags=re.I
        )
        if m:
            return m.group(1).strip()

        # сырой текст, если похож на код
        if "Part.create" in text or "part.extrude" in text:
            return text.strip()

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
        if code:
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
