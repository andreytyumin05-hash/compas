"""Нормализация кода и проверка покрытия фич ТЗ."""

from __future__ import annotations

import re
from typing import List, Set


def normalize_code(code: str) -> str:
    if not code:
        return ""
    text = str(code)
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.I)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # убрать markdown fences если остались
    text = re.sub(r"^```(?:python)?\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip() + ("\n" if text.strip() else "")


def must_fix_holes(code: str) -> bool:
    """True если в коде есть намёк на отверстия без cut/hole."""
    c = (code or "").lower()
    if "hole(" in c or "cut(" in c or "counterbore(" in c or "pattern_holes" in c:
        return False
    return bool(re.search(r"отверст|diameter\s*=\s*\d", c))


def _feature_markers(task: str) -> Set[str]:
    t = (task or "").lower()
    feats: Set[str] = set()
    for m in re.finditer(r"feature\s*=\s*([a-z_]+)", t):
        feats.add(m.group(1))
    if "цеков" in t or "counterbore" in t:
        feats.add("counterbore")
    if "зенков" in t:
        feats.add("countersink")
    if "бобыш" in t or "feature=boss" in t:
        feats.add("boss")
    if "stadium" in t or "стадион" in t or "овальн" in t or "капсул" in t:
        feats.add("stadium")
    if "крышк" in t and ("отверст" in t or "ø" in t or "диаметр" in t):
        feats.add("holes")
    if re.search(r"\d+\s*отверст", t) or "pattern_holes" in t:
        feats.add("holes")
    if "ступен" in t or "уступ" in t:
        feats.add("step")
    return feats


def check_task_feature_requirements(task: str, code: str) -> List[str]:
    missing: List[str] = []
    t = (task or "").lower()
    c = (code or "").lower()
    low_c = c
    feats = _feature_markers(task)

    if feats & {"counterbore"} or "цеков" in t:
        if "counterbore(" not in low_c:
            # hole alone is not enough for counterbore
            missing.append("counterbore")

    if feats & {"stadium"} or (
        ("крышк" in t or "фланец" in t)
        and any(w in t for w in ("stadium", "стадион", "оваль", "скругл", "r40", "капсул"))
    ):
        if "stadium(" not in low_c and "rounded_rect(" not in low_c:
            missing.append("stadium/rounded_rect")

    if feats & {"boss"} or "бобыш" in t:
        if "boss(" not in low_c and low_c.count("extrude(") < 2:
            missing.append("boss или 2×extrude")

    if feats & {"holes"} or re.search(r"ø\s*\d+|отверст", t):
        if (
            "hole(" not in low_c
            and "pattern_holes" not in low_c
            and "counterbore(" not in low_c
            and "cut(" not in low_c
        ):
            missing.append("hole/cut/pattern_holes")

    # много размеров + «крышка» → нельзя одна extrude-коробка
    if "крышк" in t and "rectangle(" in low_c and "stadium(" not in low_c:
        if low_c.count("extrude(") <= 1 and "hole(" not in low_c:
            missing.append("геометрия крышки (stadium + отверстия)")

    # 2+ диаметра отверстий в тексте
    diams = re.findall(r"(?:ø|∅)\s*(\d+)", t)
    if len(set(diams)) >= 2 and "hole(" not in low_c and "counterbore(" not in low_c:
        if "pattern_holes" not in low_c and "cut(" not in low_c:
            missing.append("несколько диаметров отверстий")

    return list(dict.fromkeys(missing))
