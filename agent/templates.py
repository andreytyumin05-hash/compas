"""Шаблоны без LLM — основной путь для типовых деталей."""

from __future__ import annotations

import re
from typing import Optional, Tuple


def _f(name: str, text: str) -> Optional[float]:
    for p in (
        rf"{name}\s*[=:]\s*([\d.]+)",
        rf"{name}\s+([\d.]+)",
    ):
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
    t = task.strip()
    low = t.lower()

    # --- Втулка ---
    if any(w in low for w in ("втулк", "bushing", "труба", "pipe")):
        outer = _f("outer_diameter", t) or _f("наружн", t)
        inner = _f("inner_diameter", t) or _f("внутр", t)
        length = _f("length", t) or _f("длин", t)
        m = re.search(
            r"наружн\w*\s*(\d+(?:\.\d+)?).*внутр\w*\s*(\d+(?:\.\d+)?).*длин\w*\s*(\d+(?:\.\d+)?)",
            low,
        )
        if m:
            outer, inner, length = map(float, m.groups())
        if not (outer and inner and length):
            nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
            if len(nums) >= 3:
                outer, inner, length = nums[0], nums[1], nums[2]
        if outer and inner and length and outer > inner > 0:
            return (
                "from core import Part\n\n"
                'part = Part.create("Втулка")\n'
                'with part.sketch("xy") as sk:\n'
                f"    sk.circle(0, 0, {outer / 2})\n"
                f"part.extrude(sk, depth={length})\n"
                f"part.hole(0, 0, diameter={inner}, through_all=True)\n"
                "part.update()\n"
            )

    # --- Крышка / stadium / flange base ---
    is_cover = any(
        w in low
        for w in (
            "крышк",
            "flange",
            "stadium",
            "oblong",
            "rounded",
            "бобыш",
            "фланец",
            "extrude_body",
            "cover",
            "plate",
            "плит",
        )
    ) or ("length=" in low and "width=" in low)

    if is_cover:
        L = _f("length", t)
        W = _f("width", t)
        pair = _pair_x(t)
        if pair and (L is None or W is None):
            a, b = pair
            L, W = (max(a, b), min(a, b))
        thick = _f("thickness", t) or _f("толщин", t)
        R = _f("outer_radius", t) or _f("corner_radius", t) or _f("radius", t)
        boss_h = _f("boss_height", t)
        if boss_h is None:
            th = _f("total_height", t)
            if th and thick and th > thick:
                boss_h = th - thick
        boss_r = (
            _f("radius_outer", t)
            or _f("inner_radius", t)
            or _f("boss_radius", t)
        )
        # если «plate» без rounded — rectangle
        use_round = any(
            w in low for w in ("stadium", "rounded", "крышк", "бобыш", "oblong", "flange")
        )

        if L and W and thick:
            x0, y0 = -L / 2.0, -W / 2.0
            lines = ["from core import Part", "", 'part = Part.create("Деталь")']
            if use_round:
                R = min(R if R is not None else min(L, W) / 2.0, L / 2.0, W / 2.0)
                lines += [
                    'with part.sketch("xy") as sk:',
                    f"    sk.rounded_rect({x0}, {y0}, {L}, {W}, radius={R})",
                    f"part.extrude(sk, depth={thick})",
                ]
            else:
                lines += [
                    'with part.sketch("xy") as sk:',
                    f"    sk.rectangle({x0}, {y0}, {L}, {W})",
                    f"part.extrude(sk, depth={thick})",
                ]
            if boss_h and boss_r and boss_h > 0 and boss_r > 0:
                lines += [
                    'with part.sketch("xy") as sk2:',
                    f"    sk2.circle(0, 0, {boss_r})",
                    f"part.extrude(sk2, depth={boss_h})",
                ]
            # отверстия по PCD
            pcd = _f("pcd", t)
            n_h = _f("hole_count", t) or _f("count", t)
            hd = _f("hole_diameter", t)
            if pcd and n_h and hd and int(n_h) >= 2:
                lines.append(
                    f"part.pattern_holes_circular((0, 0), pcd={pcd}, count={int(n_h)}, diameter={hd})"
                )
            lines += ["part.update()", ""]
            return "\n".join(lines)

    # --- Цилиндр ---
    if any(w in low for w in ("цилиндр", "диск", "кругл", "shaft", "вал")):
        d = _f("outer_diameter", t) or _f("diameter", t) or _f("диаметр", t)
        h = (
            _f("height", t)
            or _f("length", t)
            or _f("толщин", t)
            or _f("высот", t)
        )
        nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", t)]
        if d is None and nums:
            d = nums[0]
        if h is None and len(nums) >= 2:
            h = nums[1]
        if d and h:
            return (
                "from core import Part\n\n"
                'part = Part.create("Цилиндр")\n'
                'with part.sketch("xy") as sk:\n'
                f"    sk.circle(0, 0, {d / 2})\n"
                f"part.extrude(sk, depth={h})\n"
                "part.update()\n"
            )

    return None
