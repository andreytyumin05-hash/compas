"""Шаблоны только для ОДНОЗНАЧНО простых деталей. Сложным — None → LLM."""

from __future__ import annotations

import re
from typing import Optional, Tuple


def _normalize_ocr_text(text: str) -> str:
    t = (text or "").replace("\r", "").replace("\n", " ")
    t = t.replace("×", "x").replace("х", "x")
    t = re.sub(r"(?<=\d)\?(?=\d)", "x", t)
    t = re.sub(r"(?<![A-Za-zА-Яа-я])[oO](?=\d)", "Ø", t)
    return re.sub(r"\s+", " ", t).strip()


def _f(name: str, text: str) -> Optional[float]:
    aliases = {
        "length": ("length", "длина", "длин"),
        "width": ("width", "ширина", "ширин"),
        "thickness": ("thickness", "толщина", "толщин"),
        "height": ("height", "высота", "высот"),
        "outer_diameter": ("outer_diameter", "наружн"),
        "inner_diameter": ("inner_diameter", "внутр"),
        "diameter": ("diameter", "диаметр"),
        "pcd": ("pcd", "пцд"),
        "count": ("count", "кол-во", "количество"),
        "hole_diameter": ("hole_diameter", "diameter"),
    }
    for label in aliases.get(name, (name,)):
        m = re.search(rf"(?:{re.escape(label)})\s*[=:]?\s*(\d+(?:\.\d+)?)", text, re.I)
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


def _is_complex(low: str) -> bool:
    """Многоступенчатые / вал / пробка / несколько Ø — шаблоном НЕ трогать."""
    markers = (
        "ступен", "уступ", "step",
        "пробк", "штуцер", "вал", "shaft",
        "шестигран", "hex",
        "канавк", "проточк", "groove",
        "резьб", "thread",
        "несколько", "уровн",
        "feature=step", "feature=boss", "feature=pocket",
        "feature_order",
    )
    if any(m in low for m in markers):
        return True
    # два и больше явных диаметра Øxx
    diams = re.findall(r"(?:ø|∅|diameter|диаметр)\s*[=:]?\s*(\d+)", low, re.I)
    if len(set(diams)) >= 2:
        return True
    # «длина N» повторяется для ступеней
    if low.count("ступень") + low.count("уступ") + low.count("step") >= 1:
        return True
    if low.count("feature=") >= 2:
        return True
    return False


def try_template(task: str) -> Optional[str]:
    t = _normalize_ocr_text(task)
    t = re.sub(
        r"^\s*(?:распознал\s+так|detected|recognized)\s*[:\-]*\s*",
        "",
        t,
        flags=re.I,
    )
    low = t.lower()

    # Сложное ТЗ → только LLM
    if _is_complex(low):
        return None

    # --- Втулка (простая труба) ---
    if any(w in low for w in ("втулк", "bushing", "труба", "pipe")) and "ступен" not in low:
        outer = _f("outer_diameter", t)
        inner = _f("inner_diameter", t)
        length = _f("length", t) or _f("height", t)
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

    # --- Одна плита + отверстия по углам ---
    if (
        any(w in low for w in ("плит", "plate"))
        and ("отверст" in low or "hole" in low)
        and not any(w in low for w in ("бобыш", "карман", "stadium", "крышк", "фланец"))
    ):
        pair = _pair_x(t)
        L = _f("length", t) or (pair[0] if pair else 100.0)
        W = _f("width", t) or (pair[1] if pair else 60.0)
        thick = _f("thickness", t) or 8.0
        hd = _f("hole_diameter", t) or _f("diameter", t) or 9.0
        off = min(L, W) * 0.12
        return (
            "from core import Part\n\n"
            'part = Part.create("Плита")\n'
            'with part.sketch("xy") as sk:\n'
            f"    sk.rectangle({-L/2}, {-W/2}, {L}, {W})\n"
            f"part.extrude(sk, depth={thick})\n"
            f"part.pattern_holes_rect({-L/2+off}, {-W/2+off}, {L/2-off}, {W/2-off}, diameter={hd})\n"
            "part.update()\n"
        )

    # --- Простой stadium/крышка: length+width+thickness, БЕЗ ступеней ---
    if any(w in low for w in ("крышк", "cover", "stadium", "flange", "фланец")):
        # если есть несколько диаметров / ступени — уже отсечено _is_complex
        L = _f("length", t)
        W = _f("width", t)
        pair = _pair_x(t)
        if pair and (L is None or W is None):
            L, W = max(pair), min(pair)
        thick = _f("thickness", t)
        R = _f("outer_radius", t) or _f("radius", t)
        if L and W and thick:
            R = min(R if R else min(L, W) / 2, L / 2, W / 2)
            boss_h = _f("boss_height", t)
            boss_r = _f("boss_radius", t) or _f("inner_radius", t)
            lines = [
                "from core import Part",
                "",
                'part = Part.create("Крышка")',
                'with part.sketch("xy") as sk:',
                f"    sk.rounded_rect({-L/2}, {-W/2}, {L}, {W}, radius={R})",
                f"part.extrude(sk, depth={thick})",
            ]
            if boss_h and boss_r and boss_h > 0 and boss_r > 0:
                lines += [
                    'with part.sketch("xy") as sk2:',
                    f"    sk2.circle(0, 0, {boss_r})",
                    f"part.extrude(sk2, depth={boss_h})",
                ]
            pcd = _f("pcd", t)
            n_h = _f("count", t)
            hd = _f("hole_diameter", t)
            if pcd and n_h and hd and int(n_h) >= 2:
                lines.append(
                    f"part.pattern_holes_circular((0,0), pcd={pcd}, count={int(n_h)}, diameter={hd})"
                )
            lines += ["part.update()", ""]
            return "\n".join(lines)

    # --- Один цилиндр ---
    if any(w in low for w in ("цилиндр", "диск")) and not _is_complex(low):
        d = _f("outer_diameter", t) or _f("diameter", t)
        h = _f("height", t) or _f("length", t) or _f("thickness", t)
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
