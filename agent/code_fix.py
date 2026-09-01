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
    text = re.sub(r"^```(?:python)?\s*", "", text.strip(), flags=re.I)
    text = re.sub(r"\s*```$", "", text.strip())
    return text.strip() + ("\n" if text.strip() else "")


def must_fix_holes(code: str) -> bool:
    c = (code or "").lower()
    if any(
        x in c
        for x in (
            "hole(",
            "cut(",
            "counterbore(",
            "countersink(",
            "pattern_holes",
            "pocket(",
            "slot(",
        )
    ):
        return False
    return bool(re.search(r"отверст", c))


def _feature_markers(task: str) -> Set[str]:
    t = (task or "").lower()
    feats: Set[str] = set()
    for m in re.finditer(r"feature\s*=\s*([a-z_]+)", t):
        feats.add(m.group(1))
    # required_features=a,b,c
    for m in re.finditer(r"required_features\s*=\s*([a-z_,]+)", t):
        for part in m.group(1).split(","):
            p = part.strip()
            if p:
                feats.add(p)
    if "цеков" in t:
        feats.add("counterbore")
    if "зенков" in t:
        feats.add("countersink")
    if "бобыш" in t:
        feats.add("boss")
    if any(w in t for w in ("stadium", "стадион", "овальн", "капсул")):
        feats.add("stadium")
    if "карман" in t or "feature=pocket" in t:
        feats.add("pocket")
    if "паз" in t and "шпон" not in t:
        feats.add("slot")
    if "шпон" in t:
        feats.add("keyway")
    if "канавк" in t:
        feats.add("groove")
    if "скругл" in t or "fillet" in t:
        feats.add("fillet")
    if "фаск" in t or "chamfer" in t:
        feats.add("chamfer")
    if "ступен" in t or "уступ" in t:
        feats.add("step")
    return feats


def check_task_feature_requirements(task: str, code: str) -> List[str]:
    missing: List[str] = []
    t = (task or "").lower()
    low_c = (code or "").lower()
    feats = _feature_markers(task)

    def need(name: str, *needles: str) -> None:
        if not any(n in low_c for n in needles):
            missing.append(name)

    if "counterbore" in feats or "цеков" in t:
        need("counterbore", "counterbore(")

    if "countersink" in feats:
        need("countersink", "countersink(")

    if "pocket" in feats:
        need("pocket", "pocket(", "cut(")

    if "slot" in feats:
        need("slot", "slot(")

    if "keyway" in feats:
        need("keyway", "keyway(")

    if "groove" in feats or "feature=groove" in t:
        if "ring_groove(" not in low_c and "groove(" not in low_c:
            if not (low_c.count("circle(") >= 2 and "cut(" in low_c):
                missing.append("groove")

    if "fillet" in feats:
        need("fillet", "fillet(")

    if "chamfer" in feats:
        need("chamfer", "chamfer(")

    if "boss" in feats or "бобыш" in t:
        if "boss(" not in low_c and low_c.count("extrude(") < 2:
            missing.append("boss или 2×extrude")

    if "step" in feats:
        if "step(" not in low_c and low_c.count("extrude(") < 2:
            missing.append("step/несколько extrude")

    if "stadium" in feats or (
        ("крышк" in t or "фланец" in t)
        and any(w in t for w in ("stadium", "стадион", "оваль", "капсул", "r40"))
    ):
        if "stadium(" not in low_c and "rounded_rect(" not in low_c:
            missing.append("stadium/rounded_rect")

    # отверстия — только явный запрос, НЕ диаметры ступеней вала/пробки
    hole_requested = (
        "hole" in feats
        or "pattern_holes" in feats
        or bool(re.search(r"feature\s*=\s*hole", t))
        or "отверст" in t
        or "крепеж" in t
        or "штифт" in t
    )
    cylindrical_body = (
        "body_style=cylindrical" in t
        or "пробк" in t
        or re.search(r"\bвал\b", t) is not None
        or "shaft" in t
        or "plug" in t
    )
    if hole_requested and not cylindrical_body:
        if not any(
            x in low_c
            for x in (
                "hole(",
                "pattern_holes",
                "counterbore(",
                "cut(",
                "pocket(",
            )
        ):
            missing.append("hole/cut/pattern_holes")

    # крышка-коробка без stadium
    if "крышк" in t and "rectangle(" in low_c and "stadium(" not in low_c:
        if low_c.count("extrude(") <= 1 and "hole(" not in low_c:
            missing.append("геометрия крышки (stadium + отверстия)")

    return list(dict.fromkeys(missing))
