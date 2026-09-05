"""Build the generated KOMPAS script and verify vision-derived models."""

from __future__ import annotations

import os
import re
import sys
import tempfile
import time
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.syntax import Syntax

from .code_fix import normalize_code, must_fix_holes
from .critic import review_before_build
from .engineering_context import build_engineering_context
from .memory import remember
from .prompts import build_repair_prompt, get_system_prompt
from .runner import Agent
from .validate import validate_generated_code
from .verify import live_verify
from .visual_critic import review_screenshots
from .tree_snapshot import snapshot_feature_tree

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

_EDIT_WORDS = (
    "измени", "изменить", "передел", "исправь", "исправить", "поменяй", "поменять",
    "замени", "заменить", "убери", "убрать", "удали", "удалить", "добавь", "добавить",
    "доработ", "перенеси", "перемести", "смести", "увеличь", "увелич", "уменьши", "уменьш",
    "пересчитай", "пересчитать", "эту деталь", "последн", "текущую модель", "предыдущ",
    "edit request",
)


def _is_edit_task(task: str) -> bool:
    low = (task or "").lower()
    return any(word in low for word in _EDIT_WORDS)


def execute_code(code: str) -> None:
    value = normalize_code(code)
    ns = {"__name__": "__kompas_script__"}
    exec(compile(value, "<agent-build>", "exec"), ns, ns)  # noqa: S102


def _ensure_visual_tail(code: str) -> str:
    text = code or ""
    if "screenshot(" in text or "part.verify(" in text or "_auto_" in text:
        return text
    if "part.update()" not in text:
        return text
    tail = (
        "\n# auto visual\n"
        "try:\n"
        "    part.set_view('top')\n"
        "    part.screenshot('_auto_top.png')\n"
        "    part.set_view('front')\n"
        "    part.screenshot('_auto_front.png')\n"
        "    part.set_view('iso')\n"
        "    part.screenshot('_auto_iso.png')\n"
        "except Exception:\n"
        "    pass\n"
    )
    idx = text.rfind("part.update()")
    return text[: idx + len("part.update()")] + tail + text[idx + len("part.update()") :]


def _collect_shots(verify_result: dict, work: Path) -> List[Path]:
    shots: List[Path] = []
    for value in verify_result.get("shots") or []:
        if not isinstance(value, str) or value.startswith("fail:"):
            continue
        path = Path(value)
        if path.exists() and path.stat().st_size > 80 and path not in shots:
            shots.append(path)
    names = ("_auto_top.png", "_auto_front.png", "_auto_iso.png", "view_0_top.png", "view_1_front.png", "view_2_iso.png", "view_0_iso.png", "view_1_iso.png")
    for name in names:
        for candidate in (work / name, Path.cwd() / name):
            if candidate.exists() and candidate.stat().st_size > 80 and candidate not in shots:
                shots.append(candidate)
    return shots


def _active_live_context() -> str:
    """Read the currently open KOMPAS part before edit generation."""
    try:
        from core import Part
        part = Part.from_active()
        tree = snapshot_feature_tree(part)
        lines = [
            "LIVE ACTIVE KOMPAS DOCUMENT = current open detail, source of truth for edit.",
            f"ACTIVE PART NAME: {part.name}",
        ]
        if tree:
            lines.append("ACTIVE FEATURE TREE:\n" + tree[:10000])
        return "\n\n".join(lines)
    except Exception as exc:
        raise RuntimeError(f"Для режима изменения нужна открытая 3D-деталь КОМПАС: {exc}") from exc


def run_task(task: str, *, max_com_retries: int = 3, visual_loop: Optional[bool] = None, mode: str = "auto") -> str:
    normalized = re.sub(r"^\s*(?:распознал\s+так|detected|recognized)\s*[:\-]*\s*", "", (task or "").strip(), flags=re.I)
    normalized = " ".join(normalized.replace(">>", " ").replace("|", " ").split())

    edit_mode = mode == "edit" or (mode == "auto" and _is_edit_task(normalized))
    is_vision_task = "CAD_CONTRACT v2" in normalized or "CAD_CONTRACT v3" in normalized or "drawing2model" in normalized.lower()
    if visual_loop is None:
        explicit = os.getenv("COMPAS_VISUAL_LOOP")
        visual_loop = (explicit.strip().lower() in {"1", "true", "yes"}) if explicit is not None else is_vision_task

    engineering = build_engineering_context(normalized)
    if edit_mode:
        live_context = _active_live_context()
        engineering = (engineering + "\n\n" if engineering else "") + live_context

    agent = Agent()
    started = time.time()
    code, errors = agent.generate_checked(
        normalized,
        max_retries=max(2, max_com_retries),
        context=engineering,
        mode="edit" if edit_mode else "create",
    )
    if errors or must_fix_holes(code):
        raise RuntimeError("Код не прошёл проверку: " + "; ".join((errors or []) + (["hole coverage"] if must_fix_holes(code) else [])))

    if edit_mode and ("# COMPAS_EDIT_MODE" not in code or "Part.from_active()" not in code or "Part.create(" in code):
        raise RuntimeError("LLM не сформировал безопасный edit-скрипт для открытой детали")

    final = _ensure_visual_tail(code)
    work = Path(tempfile.mkdtemp(prefix="compas_vis_"))
    last_error: Optional[BaseException] = None
    max_wall = float(os.getenv("COMPAS_BUILD_TIMEOUT_SEC", "300"))
    vlm_deadline = float(os.getenv("COMPAS_VLM_TIMEOUT_SEC", "45"))

    for attempt in range(max(1, max_com_retries)):
        if time.time() - started > max_wall:
            raise TimeoutError("build exceeded COMPAS_BUILD_TIMEOUT_SEC")
        try:
            execute_code(final)

            tree_text = ""
            try:
                from core import Part
                tree_text = snapshot_feature_tree(Part.from_active())
            except Exception:
                pass

            if visual_loop and time.time() - started < max_wall:
                try:
                    from core import Part
                    part = Part.from_active()
                    vres = live_verify(part, work / "shots", views=["top", "front", "iso"])
                    tree_text = snapshot_feature_tree(part)
                    shots = _collect_shots(vres, work / "shots")
                    issues: List[str] = []
                    if shots and time.time() - started < max_wall - min(vlm_deadline, 60):
                        issues = review_screenshots(normalized, final, shots, context={"tree": tree_text[:6000], "verify": vres})
                    if issues and attempt + 1 < max_com_retries and time.time() - started < max_wall:
                        raw = agent.llm.chat([
                            {"role": "system", "content": get_system_prompt(normalized, extra_context=engineering)},
                            {"role": "user", "content": build_repair_prompt(normalized, final, issues + ["TREE/STATE:\n" + tree_text[:1200]], extra_context=engineering)},
                        ], temperature=0.1)
                        repaired = normalize_code(agent._extract_code(raw or "", allow_edit=edit_mode))
                        ok, _ = validate_generated_code(repaired)
                        if ok and (not edit_mode or ("Part.from_active()" in repaired and "Part.create(" not in repaired)):
                            good, _ = review_before_build(normalized, repaired, llm=None, use_llm=False)
                            if good:
                                final = _ensure_visual_tail(repaired)
                                continue
                except Exception as exc:
                    print(f"  visual verification failed: {exc}")

            remember(normalized, final, tree=tree_text, engineering=engineering)
            return final
        except Exception as exc:
            last_error = exc
            if attempt + 1 >= max_com_retries:
                break
            try:
                raw = agent.llm.chat([
                    {"role": "system", "content": get_system_prompt(normalized, extra_context=engineering)},
                    {"role": "user", "content": build_repair_prompt(normalized, final, [str(exc)], extra_context=engineering)},
                ], temperature=0.1)
                repaired = normalize_code(agent._extract_code(raw or "", allow_edit=edit_mode))
                ok, _ = validate_generated_code(repaired)
                if ok and (not edit_mode or ("Part.from_active()" in repaired and "Part.create(" not in repaired)):
                    final = _ensure_visual_tail(repaired)
            except Exception:
                pass
    raise RuntimeError(f"КОМПАС: {last_error}")


def run_task_export(task: str, out_path: str | Path, fmt: str = "m3d", *, mode: str = "auto") -> Tuple[str, Path]:
    from core import Part
    code = run_task(task, mode=mode)
    return code, Part.from_active().export(out_path, fmt=fmt)


def main() -> None:
    console = Console()
    if len(sys.argv) < 2:
        console.print('[yellow]python -m agent.build "описание"[/]')
        raise SystemExit(1)
    try:
        code = run_task(" ".join(sys.argv[1:]))
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        console.print("[green]Готово.[/]")
    except Exception as exc:
        console.print(f"[red]{exc}[/]")
        raise SystemExit(1)
