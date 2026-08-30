"""
LLM-клиенты + каскад провайдеров (экономия лимитов).

Порядок по умолчанию:
  1) Gemini (бесплатный лимит, отдельный от Groq)
  2) Groq лёгкая модель (gpt-oss-20b / instant)
  3) Groq сильная (gpt-oss-120b / qwen)
  4) OpenRouter free (если ключ есть)

При 429 / пустом ответе — следующий провайдер.
"""

from __future__ import annotations

import logging
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(_ENV_PATH)
else:
    load_dotenv()

log = logging.getLogger("compas.llm")

# лёгкие → сильные (только chat, не guard/tts)
_GROQ_LIGHT = (
    "openai/gpt-oss-20b",
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
    "gemma2-9b-it",
)
_GROQ_STRONG = (
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
    "llama3-70b-8192",
)
_GROQ_ALL = _GROQ_LIGHT + _GROQ_STRONG

_OPENROUTER_FREE = (
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-2-9b-it:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-7b-instruct:free",
)

_GEMINI_CODE = (
    "gemini-3.6-flash",
    "gemini-3.0-flash",
    "gemini-2.5-flash",
    "gemini-flash-latest",
)


class BaseLLM(ABC):
    name: str = "base"

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        ...


def _message_text(msg) -> str:
    if msg is None:
        return ""
    parts = []
    content = getattr(msg, "content", None)
    if content:
        parts.append(str(content))
    for attr in ("reasoning", "reasoning_content"):
        val = getattr(msg, attr, None)
        if val and isinstance(val, str) and val.strip() and not content:
            parts.append(val)
    if not parts and isinstance(msg, dict) and msg.get("content"):
        parts.append(str(msg["content"]))
    return "\n".join(parts).strip()


def _is_rate_limit(exc: BaseException) -> bool:
    s = str(exc).lower()
    return any(
        x in s
        for x in (
            "429",
            "rate limit",
            "too many requests",
            "resource_exhausted",
            "quota",
            "rate_limit",
        )
    )


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        from groq import Groq

        self.client = Groq(api_key=api_key)
        self.model = model
        self.api_key = api_key
        self.name = f"groq:{model}"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return _message_text(resp.choices[0].message)


class GeminiLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        import google.generativeai as genai

        genai.configure(api_key=api_key)
        self._genai = genai
        self.model_name = model
        self.model = genai.GenerativeModel(model)
        self.name = f"gemini:{model}"

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
        self.name = f"openrouter:{model}"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=temperature,
        )
        return _message_text(resp.choices[0].message)


class CascadeLLM(BaseLLM):
    """Пробует backends по очереди; при 429/пустом ответе — следующий."""

    name = "cascade"

    def __init__(self, backends: Sequence[BaseLLM]):
        self.backends = list(backends)
        if not self.backends:
            raise ValueError("CascadeLLM: нет backends (ключи API?)")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        errors: List[str] = []
        for backend in self.backends:
            try:
                log.info("LLM try %s", backend.name)
                text = backend.chat(messages, temperature=temperature)
                if text and text.strip():
                    return text
                errors.append(f"{backend.name}: пустой ответ")
            except Exception as e:
                errors.append(f"{backend.name}: {e}")
                log.warning("LLM fail %s: %s", backend.name, e)
                if _is_rate_limit(e):
                    time.sleep(1.5)
                    continue
                # model not found — skip
                continue
        raise RuntimeError(
            "Все LLM недоступны / лимиты. " + " | ".join(errors[:6])
        )


def list_groq_models(api_key: str) -> List[str]:
    try:
        from groq import Groq

        client = Groq(api_key=api_key)
        models = client.models.list()
        return sorted(
            m.id
            for m in models.data
            if m.id
            and not m.id.startswith("whisper")
            and "guard" not in m.id
            and "orpheus" not in m.id
        )
    except Exception:
        return []


def _pick_from(available: List[str], candidates: Sequence[str]) -> Optional[str]:
    for c in candidates:
        if c in available:
            return c
    return None


def _build_cascade() -> CascadeLLM:
    backends: List[BaseLLM] = []
    preferred = (os.getenv("LLM_MODEL") or "").strip() or None

    # 1) Gemini — отдельная квота, часто уже есть для vision
    gkey = (os.getenv("GEMINI_API_KEY") or "").strip()
    if gkey:
        gmodel = (os.getenv("LLM_GEMINI_MODEL") or "").strip()
        if not gmodel or "gemini" not in gmodel.lower():
            gmodel = _GEMINI_CODE[0]
        backends.append(GeminiLLM(gkey, gmodel))

    # 2–3) Groq light + strong
    groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if groq_key:
        available = list_groq_models(groq_key)
        light = None
        strong = None
        if preferred and (not available or preferred in available):
            # preferred как strong, light отдельно
            strong = preferred
        light = _pick_from(available, _GROQ_LIGHT) if available else _GROQ_LIGHT[0]
        if not strong:
            strong = (
                _pick_from(available, _GROQ_STRONG)
                if available
                else _GROQ_STRONG[0]
            )
        if light:
            backends.append(GroqLLM(groq_key, light))
        if strong and strong != light:
            backends.append(GroqLLM(groq_key, strong))

    # 4) OpenRouter free
    or_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if or_key:
        or_model = (os.getenv("OPENROUTER_MODEL") or "").strip() or _OPENROUTER_FREE[0]
        backends.append(OpenRouterLLM(or_key, or_model))

    if not backends:
        raise ValueError(
            "Нет ключей LLM. Задай хотя бы один:\n"
            "  GEMINI_API_KEY=...  (рекомендуется, уже для vision)\n"
            "  GROQ_API_KEY=...\n"
            "  OPENROUTER_API_KEY=...  (опционально, free-модели)\n"
            f"Файл: {_ENV_PATH}"
        )
    log.info("Cascade backends: %s", [b.name for b in backends])
    return CascadeLLM(backends)


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseLLM:
    """
    provider=cascade (default) | groq | gemini | openrouter
    cascade игнорирует provider из env если LLM_PROVIDER=cascade/auto/пустой
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "cascade") or "cascade").lower().strip()

    if provider in ("cascade", "auto", ""):
        return _build_cascade()

    model = model or os.getenv("LLM_MODEL", "") or None

    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY не задан")
        available = list_groq_models(key)
        chosen = model
        if not chosen or (available and chosen not in available):
            chosen = _pick_from(available, _GROQ_ALL) or (available[0] if available else _GROQ_LIGHT[0])
        return GroqLLM(key, chosen)

    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY не задан")
        return GeminiLLM(key, model or _GEMINI_CODE[0])

    if provider == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OPENROUTER_API_KEY не задан")
        return OpenRouterLLM(key, model or _OPENROUTER_FREE[0])

    raise ValueError(f"LLM_PROVIDER={provider!r}. cascade|groq|gemini|openrouter")
