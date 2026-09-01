"""Верификация offline + live (top/iso для плоских деталей)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .validate import critic_warnings


def code_has_visual_loop(code: str) -> bool:
    c = code or ""
    return any(x in c for x in ("screenshot(", "set_view(", "get_context(", "# visual"))


def code_has_variables(code: str) -> bool:
    c = code or ""
    return "part.var(" in c or ".var(" in c


def code_has_properties(code: str) -> bool:
    return "set_properties(" in (code or "")


def offline_verify_report(task: str, code: str) -> Dict[str, Any]:
    warns = critic_warnings(code, task)
    checks = {
        "syntax_import": "from core import Part" in (code or "")
        and "Part.create" in (code or ""),
        "update": "part.update(" in (code or ""),
        "variables": code_has_variables(code),
        "properties": code_has_properties(code),
        "visual_loop": code_has_visual_loop(code),
        "stadium_if_cover": True,
    }
    t = (task or "").lower()
    c = (code or "").lower()
    if ("крышк" in t or "stadium" in t or "оваль" in t) and "stadium(" not in c and "rounded_rect(" not in c:
        checks["stadium_if_cover"] = False

    hard = []
    if not checks["syntax_import"]:
        hard.append("нет from core import Part / Part.create")
    if not checks["update"]:
        hard.append("нет part.update()")

    if any(w in t for w in ("чертёж", "чертеж", "drawing")):
        route = "drawing2model"
    elif any(w in t for w in ("крышк", "stadium", "цеков", "бобыш")):
        route = "complex cover: stadium + boss + counterbore"
    else:
        route = "simple"

    return {
        "checks": checks,
        "hard_issues": hard,
        "soft_warnings": warns,
        "route": route,
        "ok_hard": len(hard) == 0,
    }


def live_verify(
    part: Any,
    out_dir: str | Path,
    *,
    views: Optional[List[str]] = None,
) -> Dict[str, Any]:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    # top первым — отверстия на крышке
    views = views or ["top", "iso"]
    shots: List[str] = []
    for i, v in enumerate(views):
        try:
            part.set_view(v)
        except Exception:
            pass
        path = out_dir / f"view_{i}_{v}.png"
        try:
            r = part.screenshot(path)
            shots.append(str(r if r is not None else path))
        except Exception as e:
            shots.append(f"fail:{e}")

    mass = None
    try:
        mass = part.mass_properties()
    except Exception:
        pass

    ctx = {}
    try:
        ctx = part.get_context() or {}
    except Exception:
        pass

    return {
        "shots": shots,
        "mass": mass,
        "context": {k: ctx[k] for k in list(ctx)[:20]} if isinstance(ctx, dict) else {},
        "stale_note": "refs stale after update",
    }
