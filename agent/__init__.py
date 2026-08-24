"""Агент генерации моделей КОМПАС-3D."""

__all__ = ["Agent", "get_llm_client"]


def __getattr__(name: str):
    if name == "Agent":
        from .runner import Agent

        return Agent
    if name == "get_llm_client":
        from .llm import get_llm_client

        return get_llm_client
    raise AttributeError(name)
