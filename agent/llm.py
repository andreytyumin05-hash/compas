"""LLM clients and provider cascade."""

from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from dotenv import load_dotenv

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"
load_dotenv(_ENV_PATH if _ENV_PATH.exists() else None)

log = logging.getLogger("compas.llm")

_GROQ_LIGHT = ("openai/gpt-oss-20b", "llama-3.1-8b-instant", "llama-3.3-70b-versatile")
_GROQ_STRONG = ("openai/gpt-oss-120b", "llama-3.3-70b-versatile")
_GROQ_ALL = _GROQ_LIGHT + _GROQ_STRONG
_OPENROUTER_FREE = (
    "meta-llama/llama-3.3-70b-instruct:free",
    "google/gemma-2-9b-it:free",
    "qwen/qwen-2.5-7b-instruct:free",
)
_GEMINI_CODE = ("gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash", "gemini-2.5-flash")


class BaseLLM(ABC):
    name: str = "base"

    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        ...


def _message_text(msg) -> str:
    if msg is None:
        return ""
    content = msg.get("content") if isinstance(msg, dict) else getattr(msg, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    for attr in ("reasoning", "reasoning_content"):
        value = getattr(msg, attr, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _is_rate_limit(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(x in text for x in ("429", "rate limit", "too many requests", "resource_exhausted", "resource exhausted", "quota", "rate_limit"))


def _is_model_missing(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(x in text for x in ("404", "model not found", "not found", "unsupported model", "does not exist"))


def _is_transient(exc: BaseException) -> bool:
    text = str(exc).lower()
    return _is_rate_limit(exc) or any(x in text for x in ("timeout", "timed out", "temporarily unavailable", "service unavailable", "connection reset", "502", "503", "504"))


class GroqLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        from groq import Groq
        self.client = Groq(api_key=api_key)
        self.model = model
        self.name = f"groq:{model}"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        response = self.client.chat.completions.create(model=self.model, messages=messages, temperature=temperature)
        return _message_text(response.choices[0].message if response.choices else None)


class GeminiLLM(BaseLLM):
    """Gemini client using the current google-genai SDK only."""

    def __init__(self, api_key: str, model: str):
        try:
            from google import genai
            from google.genai import types
        except ImportError as exc:
            raise RuntimeError("Gemini requires google-genai. Run: pip install -r requirements.txt") from exc
        self.model_name = model
        self._client = genai.Client(api_key=api_key)
        self._types = types
        self.name = f"gemini:{model}"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        transcript = []
        for message in messages:
            role = message.get("role", "user").upper()
            transcript.append(f"{role}:\n{message.get('content', '')}")
        response = self._client.models.generate_content(
            model=self.model_name,
            contents=["\n\n".join(transcript)],
            config=self._types.GenerateContentConfig(temperature=temperature, max_output_tokens=16000),
        )
        return getattr(response, "text", None) or ""


class OpenRouterLLM(BaseLLM):
    def __init__(self, api_key: str, model: str):
        from openai import OpenAI
        self.client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
        self.model = model
        self.name = f"openrouter:{model}"

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        response = self.client.chat.completions.create(model=self.model, messages=messages, temperature=temperature)
        return _message_text(response.choices[0].message if response.choices else None)


class CascadeLLM(BaseLLM):
    name = "cascade"

    def __init__(self, backends: Sequence[BaseLLM]):
        self.backends = list(backends)
        if not self.backends:
            raise ValueError("CascadeLLM: no backends configured")

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        failures: List[str] = []
        for backend in self.backends:
            try:
                text = backend.chat(messages, temperature=temperature)
                if text.strip():
                    return text.strip()
                failures.append(f"{backend.name}: empty response")
            except Exception as exc:
                failures.append(f"{backend.name}: {exc}")
                log.warning("LLM fallback %s: %s", backend.name, exc)
        raise RuntimeError("All LLM backends failed. " + " | ".join(failures[:8]))


def list_groq_models(api_key: str) -> List[str]:
    try:
        from groq import Groq
        models = Groq(api_key=api_key).models.list()
        return sorted(m.id for m in models.data if m.id and not m.id.startswith("whisper") and "guard" not in m.id and "orpheus" not in m.id)
    except Exception as exc:
        log.warning("Could not list Groq models: %s", exc)
        return []


def _pick_from(available: List[str], candidates: Sequence[str]) -> Optional[str]:
    return next((candidate for candidate in candidates if candidate in available), None)


def _build_cascade() -> CascadeLLM:
    backends: List[BaseLLM] = []
    preferred = (os.getenv("LLM_MODEL") or "").strip()

    gkey = (os.getenv("GEMINI_API_KEY") or "").strip()
    if gkey:
        model = (os.getenv("LLM_GEMINI_MODEL") or preferred or "").strip()
        if not model.lower().startswith("gemini"):
            model = _GEMINI_CODE[0]
        backends.append(GeminiLLM(gkey, model))

    groq_key = (os.getenv("GROQ_API_KEY") or "").strip()
    if groq_key:
        available = list_groq_models(groq_key)
        light = _pick_from(available, _GROQ_LIGHT) if available else _GROQ_LIGHT[0]
        strong = preferred if preferred in (available or _GROQ_ALL) else (_pick_from(available, _GROQ_STRONG) if available else _GROQ_STRONG[0])
        if light:
            backends.append(GroqLLM(groq_key, light))
        if strong and strong != light:
            backends.append(GroqLLM(groq_key, strong))

    or_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
    if or_key:
        backends.append(OpenRouterLLM(or_key, (os.getenv("OPENROUTER_MODEL") or "").strip() or _OPENROUTER_FREE[0]))
    if not backends:
        raise ValueError("No LLM API keys configured. Set GEMINI_API_KEY, GROQ_API_KEY, or OPENROUTER_API_KEY in .env")
    return CascadeLLM(backends)


def get_llm_client(provider: Optional[str] = None, model: Optional[str] = None, api_key: Optional[str] = None) -> BaseLLM:
    provider = (provider or os.getenv("LLM_PROVIDER", "cascade") or "cascade").lower().strip()
    if provider in {"cascade", "auto", ""}:
        return _build_cascade()
    chosen_model = (model or os.getenv("LLM_MODEL") or "").strip() or None
    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY is not set")
        available = list_groq_models(key)
        chosen = chosen_model if chosen_model in available else (_pick_from(available, _GROQ_STRONG + _GROQ_LIGHT) or (available[0] if available else _GROQ_LIGHT[0]))
        return GroqLLM(key, chosen)
    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY is not set")
        return GeminiLLM(key, chosen_model or _GEMINI_CODE[0])
    if provider == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OPENROUTER_API_KEY is not set")
        return OpenRouterLLM(key, chosen_model or _OPENROUTER_FREE[0])
    raise ValueError(f"Unsupported LLM_PROVIDER={provider!r}; use cascade|groq|gemini|openrouter")
