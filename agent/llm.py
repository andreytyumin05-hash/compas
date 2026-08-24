"""
Клиенты LLM с поддержкой бесплатных лимитов.

Провайдеры:
- groq
- gemini
- openrouter
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import List, Dict, Optional

from dotenv import load_dotenv

load_dotenv()


class BaseLLM(ABC):
    @abstractmethod
    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        """messages = [{\"role\": \"system\"|\"user\"|\"assistant\", \"content\": \"...\"}]"""
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
        self.model_name = model
        self.model = genai.GenerativeModel(model)

    def chat(self, messages: List[Dict[str, str]], temperature: float = 0.2) -> str:
        # Gemini предпочитает другой формат; упрощаем
        system = ""
        contents = []
        for m in messages:
            if m["role"] == "system":
                system = m["content"]
            elif m["role"] == "user":
                contents.append(m["content"])
            elif m["role"] == "assistant":
                contents.append(f"[Ассистент]: {m['content']}")

        prompt = (system + "\n\n" if system else "") + "\n".join(contents)
        resp = self.model.generate_content(
            prompt,
            generation_config={"temperature": temperature},
        )
        return resp.text or ""


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


def get_llm_client(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> BaseLLM:
    """
    Создать клиент LLM по настройкам из .env или аргументам.
    """
    provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower().strip()
    model = model or os.getenv("LLM_MODEL", "")
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    if provider == "groq":
        key = api_key or os.getenv("GROQ_API_KEY", "")
        if not key:
            raise ValueError("GROQ_API_KEY не задан. Получите ключ на https://console.groq.com")
        model = model or "llama-3.3-70b-versatile"
        return GroqLLM(key, model)

    if provider == "gemini":
        key = api_key or os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("GEMINI_API_KEY не задан. Получите ключ на https://aistudio.google.com")
        model = model or "gemini-2.0-flash"
        return GeminiLLM(key, model)

    if provider == "openrouter":
        key = api_key or os.getenv("OPENROUTER_API_KEY", "")
        if not key:
            raise ValueError("OPENROUTER_API_KEY не задан. Получите ключ на https://openrouter.ai")
        model = model or "meta-llama/llama-3.3-70b-instruct:free"
        return OpenRouterLLM(key, model)

    raise ValueError(f"Неизвестный провайдер: {provider}. Доступны: groq, gemini, openrouter")
