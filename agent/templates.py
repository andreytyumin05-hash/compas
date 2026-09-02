"""Deterministic templates for genuinely simple parts only."""

from __future__ import annotations

import re
from typing import Optional


def _norm(text: str) -> str:
    value = (text or "").replace("\r", "").replace("\n", " ")
    value = value.replace("×", "x").replace("х", "x")
    return re.sub(r"\s+", " ", value).strip()


def _f(label: str, text: str) -> Optional[float]:
    match = re.search(rf"(?:{label})\s*[=:]?\s*(\d+(?:\.\d+)?)", text, re.I)
    return float(match.group(1)) if match else None


def try_template(task: str) -> Optional[str]:
    text = _norm(task)
    low = text.lower()
    if any(w in low for w in (
        "cad_contract", "build_plan", "feature=", "pattern_hint", "ступен", "пробк", "вал",
        "штуцер", "шестигран", "канавк", "цеков", "зенков", "depends_on", "drawing_",
    )):
        return None

    if "втулк" in low or "bushing" in low:
        match = re.search(
            r"наружн\w*\s*(\d+(?:\.\d+)?).*внутр\w*\s*(\d+(?:\.\d+)?).*длин\w*\s*(\d+(?:\.\d+)?)",
            low,
        )
        if match:
            outer, inner, length = map(float, match.groups())
            if outer > inner > 0:
                return (
                    "from core import Part\n\n"
                    'D_OUT = %.12g\nD_IN = %.12g\nL = %.12g\n\n'
                    'part = Part.create("Втулка")\n'
                    'with part.sketch("xy") as sk:\n'
                    '    sk.circle(0, 0, D_OUT / 2)\n'
                    '    sk.dim_radial(0, 0, D_OUT / 2)\n'
                    'part.extrude(sk, depth=L)\n'
                    'part.hole(0, 0, diameter=D_IN, through_all=True)\n'
                    'part.update()\n'
                ) % (outer, inner, length)

    if ("плит" in low or "plate" in low) and "бобыш" not in low and "карман" not in low:
        match = re.search(r"(\d+(?:\.\d+)?)\s*x\s*(\d+(?:\.\d+)?)", text, re.I)
        thickness = _f("thickness", text) or _f("толщин", text) or 8.0
        if match:
            length, width = map(float, match.groups())
            return (
                "from core import Part\n\n"
                'L = %.12g\nW = %.12g\nT = %.12g\n\n'
                'part = Part.create("Плита")\n'
                'with part.sketch("xy") as sk:\n'
                '    sk.rectangle(-L/2, -W/2, L, W)\n'
                '    sk.dim_rect(-L/2, -W/2, L, W)\n'
                'part.extrude(sk, depth=T)\n'
                'part.update()\n'
            ) % (length, width, thickness)
    return None
