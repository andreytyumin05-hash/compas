"""
Клиенты LLM с поддержкой бесплатных лимитов.

Провайдеры: groq | gemini | openrouter
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional

from dotenv import load_dotenv

# Грузим .env из корня проекта (рядом с этим файлом: ../.env)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    # На всякий случай — текущая папка
    load_dotenv()


class BaseLLM(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        ...


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        from groq import Groq

        self.client = Groq(api_key=api_key)
        self.model = model

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""


class GeminiLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        system = ""
        parts: List[str] = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                parts.append(m["content"])
            elif m["role"] == "assistant":
                parts.append(f"[Ассистент]: {m['content']}")

        prompt = (system + "\n\n" if system else "") + "\n".join(parts)
        resp = self.model.generate_content(
            prompt,
            generation_config={"temperature": temperature},
        )
        return getattr(resp, "text", None) or ""


class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI

        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
        )
        self.model = model

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""


def _missing_key_message(provider: str, env_var: str, url: str) -> str:
    env_hint = (
        f"Файл .env {'найден: ' + str(_ENV_PATH) if _ENV_PATH.exists() else 'НЕ найден по пути ' + str(_ENV_PATH)}"
    )
    return (
        f"{env_var} не задан.\n"
        f"{env_hint}\n\n"
        f"Сделайте так:\n"
        f"  1) copy .env.example .env\n"
        f"  2) Откройте .env и пропишите:\n"
        f"       LLM_PROVIDER={provider}\n"
        f"       {env_var}=ваш_ключ\n"
        f"  3) Ключ взять здесь: {url}"
    )


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseLLM:
    provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower().strip()
    model = model or os.getenv("LLM_MODEL", "") or None

    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError(
                _missing_key_message("groq", "GROQ_API_KEY", "https://console.groq.com")
            )
        return GroqLLM(key, model or "llama-3.3-70b-versatile")

    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError(
                _missing_key_message(
                    "gemini", "GEMINI_API_KEY", "https://aistudio.google.com"
                )
            )
        return GeminiLLM(key, model or "gemini-2.0-flash")

    if provider == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError(
                _missing_key_message(
                    "openrouter", "OPENROUTER_API_KEY", "https://openrouter.ai"
                )
            )
        return OpenRouterLLM(
            key, model or "meta-llama/llama-3.3-70b-instruct:free"
        )

    raise ValueError(
        f"Неизвестный LLM_PROVIDER={provider!r}. "
        f"Доступны: groq, gemini, openrouter"
    )
