"""Small web-research layer for engineering standards and conventions.

Search is opt-in-by-trigger: ordinary CAD jobs do not hit the network. Search
results are advisory context for the LLM; they never silently become invented
geometry or dimensions.
"""
from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from typing import Iterable

log = logging.getLogger("compas.web")

_TRIGGER_RE = re.compile(
    r"\b(?:гост|ГОСТ|ОСТ|ISO|DIN|EN|ASME|JIS|стандарт|проточк|канавк|резьб|посадк|шлиц|шпонк|уплотн|фланц|штуцер|крепеж|болт|гайк|подшипник|зенков|цеков|фаск|радиус)\w*\b",
    re.I,
)

@dataclass(frozen=True)
class SearchResult:
    title: str
    href: str
    snippet: str


def needs_web_research(text: str) -> bool:
    return bool(_TRIGGER_RE.search(text or ""))


def _queries(text: str) -> list[str]:
    raw = " ".join((text or "").split())
    queries = [
        f"{raw} ГОСТ стандарт размеры",
        f"{raw} ГОСТ чертеж проточка канавка",
    ]
    return queries[:2]


def search_engineering(text: str, *, max_results: int = 5) -> list[SearchResult]:
    if not needs_web_research(text):
        return []
    try:
        from ddgs import DDGS
    except ImportError as exc:
        raise RuntimeError("Пакет ddgs не установлен; выполните pip install -r requirements.txt") from exc

    results: list[SearchResult] = []
    seen: set[str] = set()
    try:
        with DDGS() as ddgs:
            for query in _queries(text):
                rows: Iterable[dict] = ddgs.text(query, max_results=max(1, min(max_results, 8)), safesearch="moderate")
                for row in rows:
                    title = str(row.get("title") or "").strip()
                    href = str(row.get("href") or row.get("url") or "").strip()
                    snippet = str(row.get("body") or row.get("snippet") or "").strip()
                    if not href or href in seen:
                        continue
                    seen.add(href)
                    results.append(SearchResult(title[:180], href[:500], snippet[:500]))
                    if len(results) >= max_results:
                        return results
    except Exception as exc:
        log.warning("engineering web search failed: %s", exc)
    return results


def format_results(results: list[SearchResult], *, max_chars: int = 5000) -> str:
    if not results:
        return ""
    lines = [
        "WEB RESEARCH (advisory; verify exact standard revision before manufacturing):",
        "Use sources as evidence only. Never invent a numeric dimension that is absent from the source.",
    ]
    for index, item in enumerate(results, 1):
        lines.append(f"[{index}] {item.title}")
        lines.append(f"URL: {item.href}")
        if item.snippet:
            lines.append(f"SNIPPET: {item.snippet}")
    text = "\n".join(lines)
    return text[:max_chars]
