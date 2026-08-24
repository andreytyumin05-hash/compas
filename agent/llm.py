"""
Клиенты LLM с поддержкой бесплатных лимитов.

Провайдеры: groq | gemini | openrouter
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Optional, Sequence

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()

# Кандидаты для Groq (в порядке предпочтения). Реальные id подтянем с API.
_GROQ_FALLBACKS = (
    "llama-3.1-8b-instant",
    "llama-3.3-70b-versatile",
    "llama3-8b-8192",
    "llama3-70b-8192",
    "gemma2-9b-it",
    "mixtral-8x7b-32768",
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
)


class BaseLLM(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        ...


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        from groq import Groq

        self.client = Groq(api_key=api_key)
        self.model = model
        self.api_key = api_key

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        from groq import BadRequestError, NotFoundError, APIStatusError

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        except Exception as e:
            # Если модель недоступна — пробуем другие с аккаунта
            msg = str(e).lower()
            if "model" in msg and ("not found" in msg or "does not exist" in msg or "404" in msg):
                available = list_groq_models(self.api_key)
                raise RuntimeError(
                    f"Модель '{self.model}' недоступна на твоём ключе Groq.\n\n"
                    f"Доступные модели на аккаунте:\n"
                    + ("\n".join(f"  - {m}" for m in available) if available else "  (список пуст / не удалось получить)")
                    + "\n\nПропиши в .env одну из них, например:\n"
                    f"  LLM_MODEL={available[0] if available else 'см. список выше'}"
                ) from e
            raise


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


def list_groq_models(api_key: str) -> List[str]:
    """Список id моделей, доступных этому ключу."""
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        models = client.models.list()
        ids = sorted(
            m.id
            for m in models.data
            if m.id and not m.id.startswith("whisper")
        )
        return ids
    except Exception:
        return []


def pick_groq_model(api_key: str, preferred: Optional[str] = None) -> str:
    """
    Выбрать рабочую модель:
    1) preferred, если есть в списке API
    2) первый из fallback, который есть в списке
    3) первая модель из API
    4) preferred как есть (пусть упадёт с понятной ошибкой)
    """
    available = list_groq_models(api_key)
    if preferred and (not available or preferred in available):
        return preferred

    if available:
        for cand in _GROQ_FALLBACKS:
            if cand in available:
                return cand
        # любая chat-подобная
        for m in available:
            if "whisper" not in m.lower() and "guard" not in m.lower():
                return m
        return available[0]

    return preferred or _GROQ_FALLBACKS[0]


def _missing_key_message(provider: str, env_var: str, url: str) -> str:
    env_hint = (
        f"Файл .env найден: {_ENV_PATH}"
        if _ENV_PATH.exists()
        else f"Файл .env НЕ найден: {_ENV_PATH}"
    )
    return (
        f"{env_var} не задан.\n"
        f"{env_hint}\n\n"
        f"Сделайте так:\n"
        f"  1) copy .env.example .env\n"
        f"  2) В .env укажите:\n"
        f"       LLM_PROVIDER={provider}\n"
        f"       {env_var}=ваш_ключ\n"
        f"  3) Ключ: {url}"
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
        chosen = pick_groq_model(key, preferred=model)
        return GroqLLM(key, chosen)

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
