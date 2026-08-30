"""
Детерминированные шаблоны деталей без LLM.

Когда vision/текст уже дал размеры (stadium, втулка) — надёжнее шаблон,
чем qwen/gpt-oss с прозой и 429 на repair.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


def _f(name: str, text: str) -> Optional[float]:
    patterns = [
        rf"{name}\s*[=:]\s*([\d.]+)",
        rf"{name}\s+([\d.]+)",
    ]
    for p in patterns:
        m = re.search(p, text, re.I)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                pass
    return None


def _pair_x(text: str) -> Optional[Tuple[float, float]]:
    m = re.search(r"(\d+(?:\.\d+)?)\s*[xх×]\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        return float(m.group(1)), float(m.group(2))
    return None


def try_template(task: str) -> Optional[str]:
    """Вернуть Python-код или None, если шаблон не подходит."""
    t = task.strip()
    low = t.lower()

    # --- Втулка ---
    if any(w in low for w in ("втулк", "bushing", "труба", "pipe")):
        # наружный / внутренний / длина
        outer = None
        inner = None
        length = None
        m = re.search(
            r"наружн\w*\s*(\d+(?:\.\d+)?).*внутр\w*\s*(\d+(?:\.\d+)?).*длин\w*\s*(\d+(?:\.\d+)?)",
            low,
        )
        if m:
            outer, inner, length = float(m.group(1)), float(m.group(2)), float(m.group(3))
        else:
            nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
            if len(nums) >= 3:
                outer, inner, length = nums[0], nums[1], nums[2]
        if outer and inner and length and outer > inner > 0:
            return (
                "from core import Part\n\n"
                'part = Part.create("Втулка")\n'
                "with part.sketch(\"xy\") as sk:\n"
                f"    sk.circle(0, 0, {outer / 2})\n"
                f"part.extrude(sk, depth={length})\n"
                f"part.hole(0, 0, diameter={inner}, through_all=True)\n"
                "part.update()\n"
            )

    # --- Крышка / flange / stadium ---
    if any(
        w in low
        for w in (
            "крышк",
            "flange",
            "stadium",
            "oblong",
            "rounded",
            "бобыш",
            "фланец",
        )
    ) or ("length=" in low and "thickness=" in low):
        L = _f("length", t) or _f("длин", t)
        W = _f("width", t) or _f("width", t)
        pair = _pair_x(t)
        if pair and (L is None or W is None):
            L, W = pair[0], pair[1]
            # 116x80 vs 80x116 — length обычно больше
            if L and W and L < W:
                L, W = W, L
        thick = _f("thickness", t) or _f("толщин", t) or _f("depth", t)
        if thick is None:
            m = re.search(r"толщин\w*\s*(\d+(?:\.\d+)?)", low)
            if m:
                thick = float(m.group(1))
        R = (
            _f("outer_radius", t)
            or _f("corner_radius", t)
            or _f("radius", t)
            or _f("r", t)
        )
        boss_h = _f("boss_height", t) or _f("высот", t)
        boss_r = (
            _f("inner_radius", t)
            or _f("radius_outer", t)
            or _f("boss_radius", t)
        )
        # «бобышка R30 высота 18»
        m = re.search(
            r"бобыш\w*.*?r?\s*(\d+(?:\.\d+)?).*?высот\w*\s*(\d+(?:\.\d+)?)",
            low,
        )
        if m:
            boss_r = boss_r or float(m.group(1))
            boss_h = boss_h or float(m.group(2))
        m = re.search(r"r\s*(\d+(?:\.\d+)?).*бобыш", low)
        if m and boss_r is None:
            boss_r = float(m.group(1))

        if L and W and thick:
            R = R if R is not None else min(L, W) / 2.0
            R = min(R, L / 2.0, W / 2.0)
            x0, y0 = -L / 2.0, -W / 2.0
            lines = [
                "from core import Part",
                "",
                'part = Part.create("Крышка")',
                "with part.sketch(\"xy\") as sk:",
                f"    sk.rounded_rect({x0}, {y0}, {L}, {W}, radius={R})",
                f"part.extrude(sk, depth={thick})",
            ]
            if boss_h and boss_r and boss_h > 0 and boss_r > 0:
                lines += [
                    "with part.sketch(\"xy\") as sk2:",
                    f"    sk2.circle(0, 0, {boss_r})",
                    f"part.extrude(sk2, depth={boss_h})",
                ]
            lines.append("part.update()")
            lines.append("")
            return "\n".join(lines)

    return None
