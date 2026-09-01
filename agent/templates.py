"""Простые шаблоны без LLM. Сложное → None."""

from __future__ import annotations

import re
from typing import Optional


def _norm(task: str) -> str:
    t = (task or "").replace("\r", "").replace("\n", " ")
    t = t.replace("×", "x").replace("х", "x")
    t = re.sub(r"(?<=\d)\?(?=\d)", "x", t)
    return re.sub(r"\s+", " ", t).strip()


def _f(label: str, text: str) -> Optional[float]:
    m = re.search(rf"(?:{label})\s*[=:]?\s*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        return float(m.group(1))
    return None


def try_template(task: str) -> Optional[str]:
    t = _norm(task)
    t = re.sub(
        r"^\s*(?:распознал\s+так|detected)\s*[:\-]*\s*", "", t, flags=re.I
    )
    low = t.lower()

    if any(
        w in low
        for w in (
            "build_plan",
            "feature=",
            "feature_order",
            "pattern_hint",
            "ступен",
            "пробк",
            "вал",
            "штуцер",
            "шестигран",
            "канавк",
            "цеков",
            "зенков",
            "depends_on",
            "drawing_",
        )
    ):
        return None
    if low.count("ø") + low.count("диаметр") >= 2:
        return None

    if "втулк" in low or "bushing" in low:
        m = re.search(
            r"наружн\w*\s*(\d+(?:\.\d+)?).*внутр\w*\s*(\d+(?:\.\d+)?).*длин\w*\s*(\d+(?:\.\d+)?)",
            low,
        )
        if m:
            outer, inner, length = map(float, m.groups())
            if outer > inner > 0:
                return (
                    "from core import Part\n\n"
                    'part = Part.create("Втулка")\n'
                    f'part.var("D", {outer}, comment="наружный Ø")\n'
                    f'part.var("d", {inner}, comment="внутренний Ø")\n'
                    f'part.var("L", {length}, comment="длина")\n'
                    'part.set_properties(name="Втулка", designation="Bushing")\n'
                    'with part.sketch("xy") as sk:\n'
                    f"    sk.circle(0, 0, {outer/2})\n"
                    f"part.extrude(sk, depth={length})\n"
                    f"part.hole(0, 0, diameter={inner}, through_all=True)\n"
                    "part.update()\n"
                    'part.set_view("iso")\n'
                    'part.screenshot("_tpl_iso.png")\n'
                )

    if ("плит" in low or "plate" in low) and "бобыш" not in low and "карман" not in low:
        m = re.search(r"(\d+(?:\.\d+)?)\s*[xх]\s*(\d+(?:\.\d+)?)", t, re.I)
        thick = _f("thickness", t) or _f("толщин", t) or 8.0
        if m:
            L, W = float(m.group(1)), float(m.group(2))
            return (
                "from core import Part\n\n"
                'part = Part.create("Плита")\n'
                f'part.var("L", {L}, comment="длина")\n'
                f'part.var("W", {W}, comment="ширина")\n'
                f'part.var("T", {thick}, comment="толщина")\n'
                'part.set_properties(name="Плита")\n'
                'with part.sketch("xy") as sk:\n'
                f"    sk.rectangle({-L/2}, {-W/2}, {L}, {W})\n"
                f"part.extrude(sk, depth={thick})\n"
                "part.update()\n"
            )

    return None
