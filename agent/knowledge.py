"""Краткая CAD-база, подмешиваемая в промпт (без раздувания токенов)."""

from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_PATTERNS = _ROOT / "knowledge" / "CAD_PATTERNS.md"

# Жёстко вшитый fallback, если файл не найден
_FALLBACK = """
Дерево: эскиз→операция. Отверстия только cut. Втулка: extrude + cut.
Плита: extrude + cut holes. Фланец: body + center cut + BCD holes.
Паз: slot или rectangle cut. Диаметр→радиус/2. mm.
""".strip()


def load_patterns(max_chars: int = 3500) -> str:
    try:
        text = _PATTERNS.read_text(encoding="utf-8")
        if len(text) > max_chars:
            return text[:max_chars] + "\n…"
        return text
    except Exception:
        return _FALLBACK
