"""Offline and live verification helpers for generated KOMPAS parts."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .validate import critic_warnings


def code_has_visual_loop(code: str) -> bool:
    c = code or ""
    return any(x in c for x in ("screenshot(", "set_view(", "get_context(", "# visual"))


def code_has_variables(code: str) -> bool:
    return "part.var(" in (code or "") or ".var(" in (code or "")


def code_has_properties(code: str) -> bool:
    return "set_properties(" in (code or "")


def offline_verify_report(task: str, code: str) -> Dict[str, Any]:
    warns = critic_warnings(code, task)
    checks = {
        "syntax_import": "from core import Part" in (code or "") and "Part.create" in (code or ""),
        "update": "part.update(" in (code or ""),
        "variables": code_has_variables(code),
        "properties": code_has_properties(code),
        "visual_loop": code_has_visual_loop(code),
        "stadium_if_cover": True,
    }
    t = (task or "").lower()
    c = (code or "").lower()
    if any(x in t for x in ("крышк", "stadium", "оваль", "капсул")) and "stadium(" not in c and "rounded_rect(" not in c:
        checks["stadium_if_cover"] = False
    hard: List[str] = []
    if not checks["syntax_import"]:
        hard.append("нет from core import Part / Part.create")
    if not checks["update"]:
        hard.append("нет part.update()")
    if any(w in t for w in ("чертёж", "чертеж", "drawing")):
        route = "drawing2model"
    elif any(w in t for w in ("крышк", "stadium", "цеков", "бобыш")):
        route = "complex cover"
    elif any(w in t for w in ("штуцер", "пробк", "вал", "shaft")):
        route = "stepped cylindrical"
    else:
        route = "simple"
    return {"checks": checks, "hard_issues": hard, "soft_warnings": warns, "route": route, "ok_hard": not hard}


def live_verify(
    part: Any,
    out_dir: str | Path,
    *,
    views: Optional[List[str]] = None,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    views = views or ["top", "front", "iso"]
    shots: List[str] = []
    failures: List[str] = []
    for i, view in enumerate(views):
        try:
            part.set_view(view)
        except Exception as exc:
            failures.append(f"set_view({view}): {exc}")
        path = out_dir / f"view_{i}_{view}.png"
        try:
            result = part.screenshot(path)
            shot = Path(result) if result is not None else path
            if shot.exists() and shot.stat().st_size > 80:
                shots.append(str(shot))
            else:
                failures.append(f"screenshot({view}) produced no usable file")
        except Exception as exc:
            failures.append(f"screenshot({view}): {exc}")

    mass = None
    try:
        mass = part.mass_properties()
    except Exception as exc:
        failures.append(f"mass_properties: {exc}")

    context: Dict[str, Any] = {}
    try:
        raw = part.get_context() or {}
        if isinstance(raw, dict):
            context = {k: raw[k] for k in list(raw)[:30]}
    except Exception as exc:
        failures.append(f"get_context: {exc}")

    return {
        "shots": shots,
        "mass": mass,
        "context": context,
        "failures": failures,
        "usable_shots": len(shots),
        "stale_note": "refs are considered stale after update/rebuild",
    }
