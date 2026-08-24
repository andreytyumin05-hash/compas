"""
Показать модели, доступные твоему ключу Groq.

  python -m agent.list_models
"""

from __future__ import annotations

import os
import sys

from .llm import list_groq_models, _ENV_PATH
from dotenv import load_dotenv

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)


def main() -> None:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        print("GROQ_API_KEY не задан в .env")
        print(f"Ожидаемый путь: {_ENV_PATH}")
        sys.exit(1)

    models = list_groq_models(key)
    if not models:
        print("Не удалось получить список моделей (пустой ответ или ошибка API).")
        print("Проверь ключ на https://console.groq.com")
        sys.exit(1)

    print(f"Доступно моделей: {len(models)}\n")
    for m in models:
        print(f"  {m}")
    print("\nПропиши в .env, например:")
    print(f"  LLM_MODEL={models[0]}")


if __name__ == "__main__":
    main()
