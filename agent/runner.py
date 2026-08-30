"""Генерация: шаблон → память → LLM."""

from __future__ import annotations

import re
from typing import List, Optional, Tuple

from .code_fix import normalize_code, must_fix_holes
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

    def generate_checked(
        self, task: str, temperature: float = 0.1, max_retries: int = 1
    ) -> Tuple[str, List[str]]:
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
            sys_p = get_system_prompt(task)
            if attempt == 0:
                messages = [
                    {"role": "system", "content": sys_p},
                    {"role": "user", "content": build_user_prompt(task)},
                ]
            else:
                messages = [
                    {"role": "system", "content": sys_p},
                    {
                        "role": "user",
                        "content": build_repair_prompt(task, code, errors),
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

        tmpl = try_template(task)
        if tmpl:
            return normalize_code(tmpl), []
        if not code.strip():
            return "", [
                "модель не вернула код. "
                + repr((last_raw or "")[:200])
            ]
        return code, errors

    @staticmethod
    def _extract_code(text: str) -> str:
        if not text or not str(text).strip():
            return ""
        text = str(text)
        text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
        matches = re.findall(r"```(?:python)?\s*([\s\S]*?)```", text, flags=re.I)
        if matches:
            for block in reversed(matches):
                if "Part" in block or "from core" in block:
                    return block.strip()
            return matches[-1].strip()
        m = re.search(r"(from\s+core\s+import\s+Part[\s\S]+)", text, flags=re.I)
        if m:
            body = m.group(1).strip()
            um = re.search(
                r"(from\s+core\s+import\s+Part[\s\S]*?part\.update\s*\(\s*\))",
                body,
                flags=re.I,
            )
            return (um.group(1) if um else body).strip()
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
    agent = Agent()
    code, errors = agent.generate_checked(task)
    if code:
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
    if errors:
        for e in errors:
            console.print(f"[red]• {e}[/]")
        sys.exit(2)
    console.print("[green]OK[/]")


if __name__ == "__main__":
    main()
