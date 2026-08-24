"""
Агент для генерации моделей КОМПАС-3D.
"""

from .runner import Agent
from .llm import get_llm_client

__all__ = ["Agent", "get_llm_client"]
