"""
Цепочка верификации (Habr visual loop + MCP operator).

Offline: только эвристики по коду.
Live: set_view + screenshot (+ mass) после update.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .validate import critic_warnings


def code_has_visual_loop(code: str) -> bool:
    c = code or ""
    return any(
        x in c
        for x in (
            "screenshot(",
            "set_view(",
            "get_context(",
            "# visual",
            "# VLM",
        )
    )


def code_has_variables(code: str) -> bool:
    c = code or ""
    return "part.var(" in c or ".var(" in c or "set_variable(" in c


def code_has_properties(code: str) -> bool:
    return "set_properties(" in (code or "")


def offline_verify_report(task: str, code: str) -> Dict[str, Any]:
    """Отчёт для dry-run / CI без КОМПАС."""
    warns = critic_warnings(code, task)
    checks = {
        "syntax_import": "from core import Part" in (code or "")
        and "Part.create" in (code or ""),
        "update": "part.update(" in (code or ""),
        "variables": code_has_variables(code),
        "properties": code_has_properties(code),
        "visual_loop": code_has_visual_loop(code),
    }
    hard = []
    if not checks["syntax_import"]:
        hard.append("нет from core import Part / Part.create")
    if not checks["update"]:
        hard.append("нет part.update()")

    # routing hint
    t = (task or "").lower()
    if any(w in t for w in ("чертёж", "чертеж", "drawing", "вид спереди", "разрез")):
        route = "drawing2model — отдельный vision→plan→code, не один ReAct-блок"
    elif any(w in t for w in ("build_plan", "ступен", "пробк", "feature=")):
        route = "complex: BUILD_PLAN + visual loop + var"
    else:
        route = "simple: direct Part API"

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
    """
    После построения: 2 ракурса + screenshot.
    COM best-effort; не бросает, если снимок не удался.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    views = views or ["iso", "front"]
    shots: List[str] = []
    for i, v in enumerate(views):
        try:
            part.set_view(v)
        except Exception:
            pass
        path = out_dir / f"view_{i}_{v}.png"
        try:
            r = part.screenshot(path)
            if r is not None:
                shots.append(str(r))
            else:
                shots.append(str(path))  # intent even if COM failed
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
        "stale_note": "после update/rebuild/close refs считаются stale — перезапросить контекст",
    }
