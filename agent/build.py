"""
Сборка + короткий visual loop (без зависаний на 7 минут).
"""

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
    c = code or ""
    if "screenshot(" in c or "part.verify(" in c:
        return c
    if "part.update()" not in c:
        return c
    # top + iso — для крышек отверстия сверху
    tail = (
        "\n# auto visual\n"
        "try:\n"
        "    part.set_view('top')\n"
        "    part.screenshot('_auto_top.png')\n"
        "    part.set_view('iso')\n"
        "    part.screenshot('_auto_iso.png')\n"
        "except Exception:\n"
        "    pass\n"
    )
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
            if p.exists() and p.stat().st_size > 80:
                shots.append(p)
    for name in (
        "_auto_top.png",
        "_auto_iso.png",
        "_auto_front.png",
        "view_0_top.png",
        "view_0_iso.png",
        "view_1_iso.png",
        "view_1_front.png",
    ):
        for cand in (work / name, Path.cwd() / name):
            if cand.exists() and cand.stat().st_size > 80 and cand not in shots:
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
        # по умолчанию ВЫКЛ тяжёлый VLM в боте — иначе 7+ минут зависаний
        # включить: COMPAS_VISUAL_LOOP=1
        visual_loop = os.getenv("COMPAS_VISUAL_LOOP", "0").strip().lower() in (
            "1",
            "true",
            "yes",
        )

    agent = Agent()
    t0 = time.time()
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
    vlm_budget = float(os.getenv("COMPAS_VLM_TIMEOUT_SEC", "45"))

    for attempt in range(max_com_retries):
        try:
            execute_code(final)
            if visual_loop and (time.time() - t0) < 300:
                try:
                    from core import Part

                    part = Part.from_active()
                    vres = live_verify(
                        part, work / "shots", views=["top", "iso"]
                    )
                    tree = snapshot_feature_tree(part)
                    shots = _collect_shots(vres, work / "shots")
                    shots += _collect_shots({}, Path.cwd())
                    # жёсткий лимит на VLM
                    issues: List[str] = []
                    if shots and (time.time() - t0) < 240:
                        issues = review_screenshots(normalized, final, shots)
                    if issues:
                        print("  👁 VLM:", "; ".join(issues)[:200])
                        if attempt + 1 < max_com_retries:
                            raw = agent.llm.chat(
                                [
                                    {
                                        "role": "system",
                                        "content": get_system_prompt(normalized),
                                    },
                                    {
                                        "role": "user",
                                        "content": build_repair_prompt(
                                            normalized,
                                            final,
                                            issues + ["Дерево:\n" + tree[:600]],
                                        ),
                                    },
                                ],
                                temperature=0.1,
                            )
                            new_code = normalize_code(
                                agent._extract_code(raw or "")
                            )
                            ok, _ = validate_generated_code(new_code)
                            if ok and new_code.strip():
                                final = _ensure_visual_tail(new_code)
                                continue
                    else:
                        print("  👁 visual: ok/skip")
                except Exception as ve:
                    print(f"  👁 visual skip: {ve}")

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
                if good or not crit:
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
