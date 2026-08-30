"""Генерация: шаблон → LLM → проверка."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .code_fix import normalize_code, must_fix_holes, semantic_warnings
from .llm import get_llm_client, BaseLLM
from .prompts import get_system_prompt, build_user_prompt, build_repair_prompt
from .templates import try_template
from .validate import validate_generated_code


class Agent:
    def __init__(self, llm: Optional[BaseLLM] = None):
        self._llm = llm

    @property
    def llm(self) -> BaseLLM:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    def generate(self, task: str, temperature: float = 0.1) -> str:
        tmpl = try_template(task)
        if tmpl:
            return normalize_code(tmpl)
        messages = [
            {"role": "system", "content": get_system_prompt()},
            {"role": "user", "content": build_user_prompt(task)},
        ]
        raw = self.llm.chat(messages, temperature=temperature)
        return normalize_code(self._extract_code(raw))

    def generate_checked(
        self, task: str, temperature: float = 0.1, max_retries: int = 1
    ) -> Tuple[str, List[str]]:
        # 1) шаблон — без API, без 429
        tmpl = try_template(task)
        if tmpl:
            code = normalize_code(tmpl)
            ok, errors = validate_generated_code(code)
            if ok and not must_fix_holes(code):
                return code, []

        last_raw = ""
        code = ""
        errors: List[str] = ["пустой код"]

        for attempt in range(max_retries + 1):
            if attempt == 0:
                messages = [
                    {"role": "system", "content": get_system_prompt()},
                    {"role": "user", "content": build_user_prompt(task)},
                ]
            else:
                messages = [
                    {"role": "system", "content": get_system_prompt()},
                    {
                        "role": "user",
                        "content": (
                            "ONLY a python code block. No English. Start with from core import Part.\n\n"
                            + build_repair_prompt(task, code, errors)
                        ),
                    },
                ]
            try:
                last_raw = self.llm.chat(messages, temperature=0.1) or ""
            except Exception as e:
                errors = [f"LLM: {e}"]
                continue
            code = normalize_code(self._extract_code(last_raw))
            ok, errors = validate_generated_code(code)
            if ok and must_fix_holes(code):
                ok = False
                errors = list(errors) + ["отверстия без cut/hole"]
            if ok:
                return code, []

        if not code.strip():
            # последний шанс — шаблон ещё раз
            tmpl = try_template(task)
            if tmpl:
                return normalize_code(tmpl), []
            preview = (last_raw or "")[:300].replace("\n", " ")
            return "", [
                "пустой/проза от модели. Фрагмент: "
                + repr(preview)
                + ". Смени LLM_MODEL или опиши деталь проще (втулка/крышка с числами)."
            ]
        return code, errors

    def generate_raw(self, task: str, temperature: float = 0.1) -> str:
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
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
        text = re.sub(r"<thinking>[\s\S]*?</thinking>", "", text, flags=re.I)

        matches = re.findall(r"```(?:python)?\s*([\s\S]*?)```", text, flags=re.I)
        if matches:
            for block in reversed(matches):
                if "Part" in block or "from core" in block:
                    return block.strip()
            return matches[-1].strip()

        m = re.search(r"(from\s+core\s+import\s+Part[\s\S]+)", text, flags=re.I)
        if m:
            body = m.group(1).strip()
            # обрезать хвост после part.update()
            um = re.search(
                r"(from\s+core\s+import\s+Part[\s\S]*?part\.update\s*\(\s*\))",
                body,
                flags=re.I,
            )
            if um:
                return um.group(1).strip()
            return body

        if "Part.create" in text:
            return text.strip()
        return ""


def main() -> None:
    import sys
    from rich.console import Console
    from rich.syntax import Syntax

    console = Console()
    if len(sys.argv) < 2:
        console.print('[yellow]python -m agent.runner "описание"[/]')
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    console.print(f"[bold]Задача:[/] {task}\n")
    try:
        agent = Agent()
        code, errors = agent.generate_checked(task)
        if code:
            console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        if errors:
            for e in errors:
                console.print(f"[red]• {e}[/]")
            sys.exit(2)
        console.print("[green]OK[/]")
    except Exception as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
