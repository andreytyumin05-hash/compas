"""Build compact engineering context for CAD generation."""
from __future__ import annotations

import os
import re

from .calculations import calculation_context
from .web_search import format_results, search_engineering

_CALC_HINTS = re.compile(
    r"(?:расч(?:ет|читай)|крутящ|изгибающ|момент|вал|мощност|оборотов|напряжен|запас\s+прочност|Mb|Mt|torque|bending)",
    re.I,
)


def build_engineering_context(task: str) -> str:
    text = (task or "").strip()
    if not text:
        return ""

    parts: list[str] = []
    calc = calculation_context(text) if _CALC_HINTS.search(text) else ""
    if calc:
        parts.append(calc)

    mode = os.getenv("COMPAS_WEB_SEARCH", "auto").strip().lower()
    use_web = mode in {"1", "true", "yes", "auto"}
    if use_web:
        results = search_engineering(text, max_results=int(os.getenv("COMPAS_WEB_RESULTS", "5")))
        web = format_results(results)
        if web:
            parts.append(web)

    if not parts:
        return ""
    return "\n\n## ENGINEERING CONTEXT\n" + "\n\n".join(parts)[:9000]
