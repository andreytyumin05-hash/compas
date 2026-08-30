"""Показать ключи и каскад."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

from .llm import list_groq_models, _build_cascade, _GROQ_LIGHT, _GROQ_STRONG

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")


def main() -> None:
    print("=== Ключи ===")
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY"):
        v = os.getenv(k, "")
        print(f"  {k}: {'задан' if v.strip() else 'нет'}")

    print("\n=== Рекомендуемый .env ===")
    print("  LLM_PROVIDER=cascade")
    print("  GEMINI_API_KEY=...   # код + vision, отдельная квота")
    print("  GROQ_API_KEY=...     # запас")
    print("  # OPENROUTER_API_KEY=...  # опционально free")

    gkey = os.getenv("GROQ_API_KEY", "").strip()
    if gkey:
        ids = list_groq_models(gkey)
        print(f"\n=== Groq models ({len(ids)}) ===")
        for m in ids:
            tag = ""
            if m in _GROQ_LIGHT:
                tag = " [light]"
            elif m in _GROQ_STRONG:
                tag = " [strong]"
            print(f"  {m}{tag}")

    try:
        c = _build_cascade()
        print("\n=== Cascade order ===")
        for b in c.backends:
            print(f"  → {b.name}")
    except Exception as e:
        print(f"\nCascade: {e}")


if __name__ == "__main__":
    main()
