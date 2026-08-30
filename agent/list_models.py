"""Список моделей Groq для текущего ключа."""

from __future__ import annotations

from .llm import list_groq_models, get_llm_client
import os
from pathlib import Path
from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_ROOT / ".env")

# предпочтительные для генерации кода (не TTS / guard)
_PREFERRED = (
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
)


def main() -> None:
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        print("GROQ_API_KEY не задан в .env")
        return
    ids = list_groq_models(key)
    print(f"Доступно моделей: {len(ids)}\n")
    for m in ids:
        print(f"  {m}")

    pick = None
    for p in _PREFERRED:
        if p in ids:
            pick = p
            break
    if pick is None and ids:
        for m in ids:
            if "guard" not in m and "orpheus" not in m and "whisper" not in m:
                pick = m
                break
        pick = pick or ids[0]

    print("\nДля кода в .env лучше:")
    print(f"  LLM_MODEL={pick}")
    print("Не ставь allam / orpheus / prompt-guard — они не для CAD-кода.")


if __name__ == "__main__":
    main()
