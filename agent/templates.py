"""Шаблоны без LLM — основной путь для типовых деталей."""

from __future__ import annotations

import re
from typing import Optional, Tuple


def _normalize_ocr_text(text: str) -> str:
    """Нормализовать OCR/разметку из распознанного текста.

    Типичные артефакты: 116?80 вместо 116x80, o28 вместо Ø28,
    случайные "R"/"O"/"?" в размерах. Это нужно не только для LLM,
    но и для сырых распознанных строк из бота/vision.
    """
    t = (text or "").replace("\r", "").replace("\n", " ")
    t = t.replace("×", "x").replace("х", "x").replace("*", "x")
    t = re.sub(r"(?<=\d)\?(?=\d)", "x", t)
    t = re.sub(r"(?<![A-Za-zА-Яа-я])o(?=\d)", "Ø", t, flags=re.I)
    t = re.sub(r"(?<![A-Za-zА-Яа-я])O(?=\d)", "Ø", t)
    return t


def _f(name: str, text: str) -> Optional[float]:
    """Извлечь число из текста по имени параметра.

    Важно: в распознанных/ocr-текстах размеры могут выглядеть как
    «толщина 13 mm», «общая высота 31 mm», «габарит 116x80» или «R21».
    Здесь поддерживаем и русские, и английские подписи.
    """
    aliases = {
        "length": ("length", "длина", "длин", "габарит"),
        "width": ("width", "ширина", "ширин"),
        "thickness": ("thickness", "толщина", "толщин"),
        "height": ("height", "высота", "высот"),
        "overall_height": ("overall_height", "total_height", "общая высота", "общая высот", "общ высота"),
        "outer_radius": ("outer_radius", "radius", "радиус"),
        "boss_height": ("boss_height", "boss_h", "высота бобышки", "высота выступа", "высот бобышк"),
        "boss_radius": ("boss_radius", "boss_r", "radius boss", "радиус бобышки", "радиус выступа"),
        "depth": ("depth", "глубина", "глубин"),
        "pocket_depth": ("pocket_depth", "pocket_h", "глубина кармана", "глубина выреза"),
        "pocket_diameter": ("pocket_diameter", "pocket_d", "диаметр кармана", "диаметр выреза"),
        "hole_diameter": ("hole_diameter", "diameter", "диаметр", "d"),
        "pcd": ("pcd", "пцд"),
        "count": ("count", "кол-во", "количество"),
    }
    names = aliases.get(name, (name,))

    for label in names:
        label_re = re.escape(label)
        for pat in (
            rf"(?:{label_re})\s*[=:]?\s*(\d+(?:\.\d+)?)",
            rf"(?:{label_re})\D*?(\d+(?:\.\d+)?)",
        ):
            m = re.search(pat, text, flags=re.I)
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
    for pat in (
        r"(\d+(?:\.\d+)?)\s*(?:отверст(?:ий|ия|ие)|holes?|count|крепежн|штифтов|болтов)",
        r"(\d+)\s*(?:крепежн|штифтов|основн|главн)\s*(?:отверст(?:ий|ия|ие)|holes?)",
    ):
        m = re.search(pat, text, re.I)
        if m:
            count = float(m.group(1))
            break

    pcd = None
    m = re.search(r"(?:pcd|пцд)[^\d]*(\d+(?:\.\d+)?)", text, re.I)
    if m:
        pcd = float(m.group(1))

    diam = None
    for pat in (
        r"(?:крепежн|штифтов|основн|главн|основные|главные)?\s*(?:отверст(?:ий|ия|ие)|holes?)\D*(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)",
        r"(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)\D*(?:крепежн|штифтов|основн|главн)\s*(?:отверст(?:ий|ия|ие)|holes?)",
        r"(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)",
    ):
        m = re.search(pat, text, re.I)
        if m:
            diam = float(m.group(1))
            # do not accept the overall body size as a hole diameter when it's not near a hole keyword
            if diam and diam > 80 and "отверст" not in text.lower() and "hole" not in text.lower() and "pcd" not in text.lower():
                continue
            break
    if pcd is not None and diam is not None:
        tail = text[text.find('pcd') if 'pcd' in text.lower() else 0 :]
        m2 = re.search(r"(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)", tail, re.I)
        if m2:
            diam = float(m2.group(1))
    return count, pcd, diam


def _extract_complex_cover_hole_pattern(text: str) -> Tuple[Optional[int], Optional[float], Optional[float]]:
    patterns = (
        r"(\d+)\s*(?:крепежн|отверст|holes?|bolt|stud|pin|штифтов)\D*(?:[øø∅]|diam(?:eter)?|d)\D*(\d+(?:\.\d+)?)",
        r"(\d+)\s*(?:крепежн|отверст|holes?|bolt|stud|pin|штифтов)\D*(\d+(?:\.\d+)?)",
        r"(?:[øø∅]|diam(?:eter)?|d)\D*(\d+(?:\.\d+)?)\D*(?:\b(\d+)\b)\D*(?:крепежн|отверст|holes?|bolt|stud|pin|штифтов)",
    )
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            count = int(float(m.group(1)))
            diam = float(m.group(2)) if len(m.groups()) > 1 and m.group(2) else None
            if diam is not None:
                return count, None, diam
    return None, None, None


def _extract_radius_value(text: str) -> Optional[float]:
    patterns = (
        r"(?:radius|радиус)[^\d]*(\d+(?:\.\d+)?)",
        r"(?<![A-Za-z])R\s*(\d+(?:\.\d+)?)\b",
        r"(?<![A-Za-z])r\s*(\d+(?:\.\d+)?)\b",
    )
    for label in ("бобышк", "boss", "bushing"):
        idx = text.lower().find(label)
        if idx >= 0:
            segment = text[max(0, idx - 30): min(len(text), idx + 80)]
            for pat in patterns:
                m = re.search(pat, segment, re.I)
                if m:
                    return float(m.group(1))
    for pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            return float(m.group(1))
    return None


def _extract_pocket_geometry(text: str) -> Tuple[Optional[float], Optional[float]]:
    for label in ("карман", "pocket", "recess", "глух"):
        idx = text.lower().find(label)
        if idx < 0:
            continue
        segment = text[max(0, idx - 25): idx + 120]
        d = None
        depth = None
        m = re.search(r"(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)", segment, re.I)
        if m:
            d = float(m.group(1))
        m2 = re.search(r"(?:depth|глубин|h|height|высот)[^\d]*(\d+(?:\.\d+)?)", segment, re.I)
        if m2:
            depth = float(m2.group(1))
        m3 = re.search(r"(?:карман|pocket|recess|глух)[^\d]*(\d+(?:\.\d+)?)\D*(?:depth|глубин|h|height|высот)[^\d]*(\d+(?:\.\d+)?)", segment, re.I)
        if m3:
            d = float(m3.group(1))
            depth = float(m3.group(2))
        if d is not None or depth is not None:
            return d, depth
    return None, None


def _extract_hole_group(text: str, *, keywords: Tuple[str, ...]) -> Tuple[Optional[int], Optional[float], Optional[float]]:
    low = text.lower()
    for kw in keywords:
        idx = low.find(kw)
        if idx < 0:
            continue
        segment = text[max(0, idx - 30): idx + 120]
        m_count = re.search(r"(\d+)\s*(?:отверст(?:ий|ия|ие)|holes?|bolt|stud|pin|штифтов|крепежн)", segment, re.I)
        count = int(float(m_count.group(1))) if m_count else None
        m_d = re.search(r"(?:[øø∅]|diam(?:eter)?|d)[^\d]*(\d+(?:\.\d+)?)", segment, re.I)
        diam = float(m_d.group(1)) if m_d else None
        if count is not None and diam is not None:
            return count, None, diam
    return None, None, None


def try_template(task: str) -> Optional[str]:
    t = _normalize_ocr_text(task).strip()
    # Поддержка сырых сообщений вида «Распознал так: ...» и стрелок/markdown.
    t = re.sub(r"^\s*(?:распознал\s+так|detected|recognized)\s*[:\-]*\s*", "", t, flags=re.I)
    t = t.replace(">>", " ").replace("|", " ")
    t = re.sub(r"\s+", " ", t).strip()
    low = t.lower()

    # --- Плита / шаблонные отверстия по углам ---
    if (
        any(w in low for w in ("плит", "plate", "основани", "base"))
        and ("отверст" in low or "hole" in low)
        and ("угол" in low or "corn" in low or "по углам" in low or "4" in low)
        and not any(w in low for w in ("бобыш", "boss", "карман", "pocket", "скругл", "fillet", "фаск", "chamfer", "stadium", "rounded", "oblong", "flange", "cover", "крышк"))
    ):
        size3 = _extract_compact_size(t) or _pair_x(t)
        if size3 is not None:
            if len(size3) == 3:
                L, W, thick = size3
            else:
                L, W = size3
                thick = _f("thickness", t) or _f("толщин", t) or 8.0
        else:
            L = _f("length", t) or 100.0
            W = _f("width", t) or 60.0
            thick = _f("thickness", t) or _f("толщин", t) or 8.0

        hole_d = _f("hole_diameter", t) or _f("diameter", t) or _f("d", t) or 9.0
        offset = _f("offset", t) or _f("отступ", t) or min(L, W) * 0.12
        x1 = -L / 2.0 + offset
        y1 = -W / 2.0 + offset
        x2 = L / 2.0 - offset
        y2 = W / 2.0 - offset

        return (
            "from core import Part\n\n"
            'part = Part.create("Плита")\n'
            'with part.sketch("xy") as sk:\n'
            f"    sk.rectangle({-L / 2.0}, { -W / 2.0}, {L}, {W})\n"
            f"part.extrude(sk, depth={thick})\n"
            f"part.pattern_holes_rect({x1}, {y1}, {x2}, {y2}, diameter={hole_d}, through_all=True)\n"
            "part.update()\n"
        )

    # --- Уступ + паз ---
    if ("уступ" in low or "step" in low or "slot" in low or "паз" in low) and (
        "плита" in low or "plate" in low or "основан" in low or "base" in low or "деталь" in low
    ):
        L = _f("length", t) or 120.0
        W = _f("width", t) or 80.0
        T = _f("thickness", t) or _f("толщин", t) or 10.0
        step_w = _f("step_width", t) or _f("ширин", t) or 20.0
        step_h = _f("step_height", t) or _f("высот", t) or 12.0
        slot_w = _f("slot_width", t) or _f("slot", t) or 6.0
        return (
            "from core import Part\n\n"
            'part = Part.create("Деталь")\n'
            'with part.sketch("xy") as sk:\n'
            f"    sk.rectangle(-{L / 2.0}, -{W / 2.0}, {L}, {W})\n"
            f"part.extrude(sk, depth={T})\n"
            f"part.step(0, 0, width={step_w}, height={step_h}, depth={step_h}, shape='rect')\n"
            f"part.slot(-{L / 4.0}, 0, {L / 4.0}, 0, width={slot_w}, depth={T}, through_all=False)\n"
            "part.update()\n"
        )

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
        R = _f("outer_radius", t) or _f("corner_radius", t) or _f("radius", t) or _extract_radius_value(t)
        boss_r, boss_h = _extract_feature_pair(t, ("бобышк", "boss", "bushing"))
        boss_h = (
            _f("boss_height", t)
            or _f("boss_h", t)
            or boss_h
        )
        if boss_h is None:
            th = _f("total_height", t) or _f("overall_height", t)
            if th and thick and th > thick:
                boss_h = th - thick
        boss_r = (
            _f("radius_outer", t)
            or _f("inner_radius", t)
            or _f("boss_radius", t)
            or _f("boss_r", t)
            or boss_r
        )
        if boss_r is None:
            boss_r = _extract_radius_value(t)
        if boss_r is not None and boss_h is not None and boss_r > boss_h:
            boss_r = boss_r / 2.0 if boss_r > boss_h else boss_r
        if boss_r is None and boss_h is not None and ("бобыш" in low or "boss" in low):
            boss_r = 0.55 * min(L, W) if L and W else 20.0
        pocket_d, pocket_depth = _extract_pocket_geometry(t)
        pocket_depth = (
            _f("pocket_depth", t)
            or _f("pocket_h", t)
            or _f("depth_pocket", t)
            or pocket_depth
        )
        if pocket_d is None:
            pocket_d = (
                _f("pocket_diameter", t)
                or _f("pocket_d", t)
                or _f("pocket_inner_diameter", t)
            )
        pocket_r = _f("pocket_radius", t)
        if pocket_r is not None and pocket_d is None:
            pocket_d = 2 * pocket_r
        if pocket_d is not None and pocket_d > 80 and ("карман" in low or "pocket" in low):
            pocket_d = min(pocket_d, min(L, W) * 0.6) if L and W else pocket_d
        # Для сложных крышек/переходов центральная выемка допустима по умолчанию, если есть
        # явная бобышка и суммарная высота больше толщины тела.
        if pocket_depth is None and boss_h and thick and boss_h > thick:
            pocket_depth = min(8.0, max(3.0, boss_h - thick))
            pocket_d = min(L, W) * 0.5 if L and W else 50.0
        if pocket_depth is None and thick is not None and ("overall_height" in low or "total_height" in low) and ("крышк" in low or "cover" in low or "stadium" in low):
            pocket_depth = min(8.0, max(3.0, (float(re.search(r"(\d+(?:\.\d+)?)", re.search(r"overall_height\s*[=:]?\s*(\d+(?:\.\d+)?)|total_height\s*[=:]?\s*(\d+(?:\.\d+)?)", t, re.I).group(0) or "0", re.I).group(1)) if re.search(r"overall_height\s*[=:]?\s*(\d+(?:\.\d+)?)|total_height\s*[=:]?\s*(\d+(?:\.\d+)?)", t, re.I) else 0) - thick))
            pocket_d = min(L, W) * 0.65 if L and W else 45.0
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
            # отверстия по PCD и по группам в тексте задачи
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

            main_count, _, main_d = _extract_hole_group(t, keywords=("основн", "главн", "main"))
            mount_count, _, mount_d = _extract_hole_group(t, keywords=("крепеж", "bolt", "mount"))
            pin_count, _, pin_d = _extract_hole_group(t, keywords=("штифт", "pin", "stud"))

            if main_count is not None and main_d is not None:
                main_pcd = min(L, W) * 0.36 if L and W else 30.0
                lines.append(
                    f"part.pattern_holes_circular((0, 0), pcd={main_pcd}, count={main_count}, diameter={main_d})"
                )

            if mount_count is not None and mount_d is not None:
                mount_pcd = pcd or (min(L, W) * 0.52 if L and W else 60.0)
                lines.append(
                    f"part.pattern_holes_circular((0, 0), pcd={mount_pcd}, count={mount_count}, diameter={mount_d})"
                )

            if pin_count is not None and pin_d is not None:
                pin_pcd = min(L, W) * 0.2 if L and W else 20.0
                lines.append(
                    f"part.pattern_holes_circular((0, 0), pcd={pin_pcd}, count={pin_count}, diameter={pin_d})"
                )

            if pcd and n_h and hd and int(n_h) >= 2 and (main_count is None and mount_count is None and pin_count is None):
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
