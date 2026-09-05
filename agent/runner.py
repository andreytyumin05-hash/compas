"""Generate -> validate -> critique -> return CAD code."""

from __future__ import annotations

import ast
import re
from typing import List, Optional, Tuple

from .code_fix import check_task_feature_requirements, normalize_code, must_fix_holes
from .critic import review_before_build
from .llm import BaseLLM, get_llm_client
from .prompts import build_repair_prompt, build_user_prompt, get_system_prompt
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
        self,
        task: str,
        temperature: float = 0.1,
        max_retries: int = 3,
        context: str = "",
    ) -> Tuple[str, List[str]]:
        contract = task.strip()
        template = try_template(contract) if not context else None
        if template:
            code = normalize_code(template)
            ok, errors = self._validate_all(contract, code)
            if ok:
                return code, []

        code = ""
        errors: List[str] = ["empty code"]
        last_raw = ""
        system_prompt = get_system_prompt(contract, extra_context=context)

        for attempt in range(max_retries + 1):
            if attempt == 0:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": build_user_prompt(contract, extra_context=context)},
                ]
            else:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": build_repair_prompt(contract, code, errors, extra_context=context)},
                ]
            try:
                last_raw = self.llm.chat(messages, temperature=temperature)
            except Exception as exc:
                errors = [f"LLM: {exc}"]
                continue

            code = normalize_code(self._extract_code(last_raw))
            ok, errors = self._validate_all(contract, code)
            if not ok:
                continue

            good, critic_errors = review_before_build(
                contract,
                code,
                llm=self.llm,
                use_llm=None,
            )
            if good:
                return code, []
            errors = critic_errors or ["critic rejected code"]

        if not code.strip():
            return "", [f"model did not return code: {(last_raw or '')[:240]!r}"]
        return code, errors

    @staticmethod
    def _validate_all(task: str, code: str) -> Tuple[bool, List[str]]:
        ok, errors = validate_generated_code(code)
        if not ok:
            return False, errors
        missing = check_task_feature_requirements(task, code)
        if missing:
            return False, ["missing operations: " + ", ".join(missing)]
        if must_fix_holes(code):
            return False, ["hole coverage validation failed"]
        return True, []

    @staticmethod
    def _extract_code(text: str) -> str:
        """Extract the first syntactically valid CAD script, not model prose/reasoning."""
        if not text or not str(text).strip():
            return ""
        raw = re.sub(r"<think>[\s\S]*?</think>", "", str(text), flags=re.I).strip()
        blocks = re.findall(r"```(?:python|py)?\s*([\s\S]*?)```", raw, flags=re.I)
        candidates = blocks or [raw]

        for candidate in candidates:
            code = candidate.strip()
            marker = re.search(r"(?m)^\s*from\s+core\s+import\s+Part\s*$", code)
            if marker:
                code = code[marker.start():]
            code = re.sub(r"\n(?:Explanation|Notes?|Here is|Corrected code)\s*:\s*[\s\S]*$", "", code, flags=re.I)
            code = code.strip()
            try:
                tree = ast.parse(code)
            except SyntaxError:
                continue
            has_create = any(
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "Part"
                and node.func.attr == "create"
                for node in ast.walk(tree)
            )
            if has_create:
                return code

        return ""
