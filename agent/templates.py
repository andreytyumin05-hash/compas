"""Шаблоны без LLM — основной путь для типовых деталей."""

from __future__ import annotations

import re
from typing import Optional, Tuple


def _f(name: str, text: str) -> Optional[float]:
    # Be explicit: single-letter names like "h", "d", "r" are too broad and cause
    # false positives on unrelated dimensions (e.g. fillet R2 or boss h18).
    for p in (
        rf"{name}\s*[=:]\s*([\d.]+)",
        rf"{name}\s+([\d.]+)",
        rf"{name}([\d.]+)",
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


def _extract_compact_size(text: str) -> Optional[Tuple[float, float, float]]:
    # Handles patterns like 116x80x13 or 116x80 x13
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*[xх×]\s*(\d+(?:\.\d+)?)\s*(?:[xх×]|\s*by\s*)\s*(\d+(?:\.\d+)?)",
        text,
        re.I,
    )
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3))
    return None


def _extract_dim_after(text: str, labels: Tuple[str, ...]) -> Optional[float]:
    low = text.lower()
    for label in labels:
        pats = (
            rf"(?:{label})[^\d]{{0,20}}(?:[øø∅]|diam(?:eter)?|d)[^\d]*([\d.]+)",
            rf"(?:{label})[^\d]{{0,20}}(?:h|height|высот|depth|глубин)[^\d]*([\d.]+)",
            rf"(?:{label})\s*(?:[=:]|\s+)?\s*(\d+(?:\.\d+)?)",
        )
        for pat in pats:
            m = re.search(pat, low, re.I)
            if m:
                try:
                    return float(m.group(1))
                except ValueError:
                    pass
    return None


def _extract_feature_pair(text: str, feature_labels: Tuple[str, ...]) -> Tuple[Optional[float], Optional[float]]:
    for label in feature_labels:
        pats = (
            rf"(?:{label})[^\d]{{0,25}}(?:[øø∅]|diam(?:eter)?|d)[^\d]*([\d.]+)(?:[^\d]{{0,20}}(?:h|height|высот|depth|глубин)[^\d]*([\d.]+))?",
            rf"(?:{label})[^\d]{{0,25}}(?:h|height|высот|depth|глубин)[^\d]*([\d.]+)(?:[^\d]{{0,20}}(?:[øø∅]|diam(?:eter)?|d)[^\d]*([\d.]+))?",
            rf"(?:{label})[^\d]{{0,25}}([\d.]+)(?:[^\d]{{0,20}}(?:h|height|высот|depth|глубин)[^\d]*([\d.]+))?",
        )
        for pat in pats:
            m = re.search(pat, text, re.I)
            if m:
                a = m.group(1)
                b = m.group(2) if m.lastindex and m.lastindex >= 2 else None
                try:
                    return float(a), float(b) if b is not None else None
                except ValueError:
                    pass
    return None, None


def _extract_pattern_hole_data(text: str) -> Tuple[Optional[float], Optional[float], Optional[float]]:
    count = None
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:отверст(?:ий|ия|ие)|holes?|count)", text, re.I)
    if m:
        count = float(m.group(1))

    pcd = None
    m = re.search(r"(?:pcd|пцд)[^\d]*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        pcd = float(m.group(1))

    diam = None
    m = re.search(r"(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        diam = float(m.group(1))
    if pcd is not None and diam is not None:
        tail = text[text.find('pcd') if 'pcd' in text.lower() else 0 :]
        m2 = re.search(r"(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)", tail, re.I)
        if m2:
            diam = float(m2.group(1))
    return count, pcd, diam


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
    size3 = _extract_compact_size(t)
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
            "основание",
            "base",
        )
    ) or ("length=" in low and "width=" in low) or size3 is not None

    if is_cover:
        L = _f("length", t)
        W = _f("width", t)
        pair = _pair_x(t)
        if pair and (L is None or W is None):
            a, b = pair
            L, W = (max(a, b), min(a, b))
        if size3 is not None and (L is None or W is None or _f("thickness", t) is None):
            L, W, thick = size3
        else:
            thick = _f("thickness", t) or _f("толщин", t)
        if L is None and W is None and pair is None and size3 is not None:
            L, W, thick = size3
        if L is None and pair is not None:
            L, W = pair
            if thick is None:
                thick = _f("thickness", t) or _f("толщин", t)
        R = _f("outer_radius", t) or _f("corner_radius", t) or _f("radius", t)
        boss_r, boss_h = _extract_feature_pair(t, ("бобышк", "boss", "bushing"))
        boss_h = (
            _f("boss_height", t)
            or _f("boss_h", t)
            or boss_h
        )
        if boss_h is None:
            th = _f("total_height", t)
            if th and thick and th > thick:
                boss_h = th - thick
        boss_r = (
            _f("radius_outer", t)
            or _f("inner_radius", t)
            or _f("boss_radius", t)
            or _f("boss_r", t)
            or boss_r
        )
        if boss_r is not None and boss_h is not None and boss_r > boss_h:
            boss_r = boss_r / 2.0 if boss_r > boss_h else boss_r
        pocket_d, pocket_depth = _extract_feature_pair(t, ("карман", "pocket", "recess"))
        pocket_depth = (
            _f("pocket_depth", t)
            or _f("pocket_h", t)
            or _f("depth_pocket", t)
            or _f("depth", t)
            or pocket_depth
        )
        pocket_d = (
            _f("pocket_diameter", t)
            or _f("pocket_d", t)
            or _f("pocket_inner_diameter", t)
            or _f("diameter", t)
            or pocket_d
        )
        pocket_r = _f("pocket_radius", t)
        if pocket_r is not None and pocket_d is None:
            pocket_d = 2 * pocket_r
        # если «plate» без rounded — rectangle
        use_round = any(
            w in low for w in ("stadium", "rounded", "крышк", "бобыш", "oblong", "flange", "основание")
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
            if pocket_depth and pocket_d and pocket_depth > 0 and pocket_d > 0:
                lines += [
                    'with part.sketch("xy") as sk3:',
                    f"    sk3.circle(0, 0, {pocket_d / 2.0})",
                    f"part.cut(sk3, depth={pocket_depth}, through_all=False)",
                ]
            # отверстия по PCD
            pcd = _f("pcd", t)
            n_h = _f("hole_count", t) or _f("count", t)
            hd = _f("hole_diameter", t) or _f("diameter", t)
            if pcd is None or n_h is None or hd is None:
                count, pcd2, diam = _extract_pattern_hole_data(t)
                if pcd is None:
                    pcd = pcd2
                if n_h is None:
                    n_h = count
                if hd is None:
                    hd = diam
            if pcd and n_h and hd and int(n_h) >= 2:
                lines.append(
                    f"part.pattern_holes_circular((0, 0), pcd={pcd}, count={int(n_h)}, diameter={hd})"
                )

            fillet_r = _f("fillet_radius", t) or _f("rounding_radius", t)
            if fillet_r is None:
                m = re.search(r"(?:скругл|fillet|rounding)[^\d]*(\d+(?:\.\d+)?)", t, re.I)
                if m:
                    fillet_r = float(m.group(1))
            if fillet_r is not None:
                lines.append(f"part.fillet(radius={fillet_r})")

            chamfer_d = _f("chamfer_size", t) or _f("chamfer", t)
            if chamfer_d is None:
                m = re.search(r"(?:фаск|chamfer|bevel)[^\d]*(\d+(?:\.\d+)?)", t, re.I)
                if m:
                    chamfer_d = float(m.group(1))
            if chamfer_d is not None:
                lines.append(f"part.chamfer(size={chamfer_d})")

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
