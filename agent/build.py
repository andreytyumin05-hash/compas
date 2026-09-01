"""
Сборка в КОМПАС + visual loop (Habr):
generate → COM → screenshot iso/front → VLM critic → optional repair.
"""

from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple

from rich.console import Console
from rich.syntax import Syntax

from .code_fix import normalize_code, must_fix_holes
from .critic import review_before_build
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


def execute_code(code: str) -> None:
    code = normalize_code(code)
    ns = {"__name__": "__kompas_script__"}
    exec(compile(code, "<agent-build>", "exec"), ns, ns)  # noqa: S102


def _ensure_visual_tail(code: str) -> str:
    """Если агент забыл screenshot — добавим хвост verify (не ломает синтаксис)."""
    c = code or ""
    if "screenshot(" in c or "part.verify(" in c:
        return c
    if "part.update()" not in c:
        return c
    tail = (
        "\n# auto visual loop\n"
        "try:\n"
        "    part.set_view('iso')\n"
        "    part.screenshot('_auto_iso.png')\n"
        "    part.set_view('front')\n"
        "    part.screenshot('_auto_front.png')\n"
        "except Exception:\n"
        "    pass\n"
    )
    # после последнего update
    idx = c.rfind("part.update()")
    if idx < 0:
        return c + tail
    end = idx + len("part.update()")
    return c[:end] + "\n" + tail + c[end:]


def _collect_shots(verify_result: dict, work: Path) -> List[Path]:
    shots: List[Path] = []
    for s in verify_result.get("shots") or []:
        if isinstance(s, str) and not s.startswith("fail:"):
            p = Path(s)
            if p.exists():
                shots.append(p)
    for name in ("_auto_iso.png", "_auto_front.png", "view_0_iso.png", "view_1_front.png"):
        p = work / name if not Path(name).is_absolute() else Path(name)
        # also cwd
        for cand in (p, Path.cwd() / name, work / name):
            if cand.exists() and cand not in shots:
                shots.append(cand)
    return shots


def run_task(
    task: str,
    *,
    max_com_retries: int = 2,
    visual_loop: Optional[bool] = None,
) -> str:
    normalized = task.strip()
    normalized = re.sub(
        r"^\s*(?:распознал\s+так|detected|recognized)\s*[:\-]*\s*",
        "",
        normalized,
        flags=re.I,
    )
    normalized = normalized.replace(">>", " ").replace("|", " ")
    normalized = " ".join(normalized.split())

    if visual_loop is None:
        visual_loop = os.getenv("COMPAS_VISUAL_LOOP", "1").strip() not in (
            "0",
            "false",
            "no",
        )

    agent = Agent()
    code, errors = agent.generate_checked(normalized)
    if errors or must_fix_holes(code):
        raise RuntimeError(
            "Код не прошёл проверку: "
            + "; ".join(
                (errors or [])
                + (["отверстия без cut"] if must_fix_holes(code) else [])
            )
        )

    code = _ensure_visual_tail(code)
    last_err: Optional[BaseException] = None
    final = code
    work = Path(tempfile.mkdtemp(prefix="compas_vis_"))

    for attempt in range(max_com_retries):
        try:
            execute_code(final)
            # visual loop
            if visual_loop:
                try:
                    from core import Part

                    part = Part.from_active()
                    vres = live_verify(part, work / "shots", views=["iso", "front"])
                    tree = snapshot_feature_tree(part)
                    shots = _collect_shots(vres, work / "shots")
                    # cwd auto screenshots from injected tail
                    shots += _collect_shots({}, Path.cwd())
                    issues = review_screenshots(normalized, final, shots)
                    if issues:
                        print("  👁 VLM critic:", "; ".join(issues))
                        if attempt + 1 < max_com_retries:
                            repair_errs = issues + [
                                "Дерево:\n" + tree[:800]
                            ]
                            raw = agent.llm.chat(
                                [
                                    {
                                        "role": "system",
                                        "content": get_system_prompt(normalized),
                                    },
                                    {
                                        "role": "user",
                                        "content": build_repair_prompt(
                                            normalized, final, repair_errs
                                        ),
                                    },
                                ],
                                temperature=0.1,
                            )
                            new_code = normalize_code(
                                agent._extract_code(raw or "")
                            )
                            ok, verr = validate_generated_code(new_code)
                            if ok and new_code.strip():
                                good, crit = review_before_build(
                                    normalized,
                                    new_code,
                                    llm=None,
                                    use_llm=False,
                                )
                                if good or not crit:
                                    final = _ensure_visual_tail(new_code)
                                    continue  # re-exec
                    else:
                        print("  👁 visual loop: ok / skip")
                except Exception as ve:
                    print(f"  👁 visual loop skip: {ve}")

            remember(task, final)
            return final
        except Exception as e:
            last_err = e
            if attempt + 1 >= max_com_retries:
                break
            try:
                raw = agent.llm.chat(
                    [
                        {"role": "system", "content": get_system_prompt(task)},
                        {
                            "role": "user",
                            "content": build_repair_prompt(
                                task, final, [str(e)]
                            ),
                        },
                    ],
                    temperature=0.1,
                )
                new_code = normalize_code(agent._extract_code(raw or ""))
                ok, _ = validate_generated_code(new_code)
                if not ok:
                    continue
                good, crit = review_before_build(
                    task, new_code, llm=None, use_llm=False
                )
                if good:
                    final = _ensure_visual_tail(new_code)
                elif not crit:
                    final = _ensure_visual_tail(new_code)
            except Exception:
                pass
    raise RuntimeError(f"КОМПАС: {last_err}")


def run_task_export(
    task: str, out_path: str | Path, fmt: str = "m3d"
) -> Tuple[str, Path]:
    from core import Part

    code = run_task(task)
    path = Part.from_active().export(out_path, fmt=fmt)
    return code, path


def main() -> None:
    console = Console()
    if len(sys.argv) < 2:
        console.print('[yellow]python -m agent.build "описание"[/]')
        sys.exit(1)
    task = " ".join(sys.argv[1:])
    try:
        code = run_task(task)
        console.print(Syntax(code, "python", theme="monokai", line_numbers=True))
        console.print("[green]Готово.[/]")
    except Exception as e:
        console.print(f"[red]{e}[/]")
        sys.exit(1)


if __name__ == "__main__":
    main()
