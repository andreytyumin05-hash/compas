"""
Офлайн-проверка кода агента БЕЗ КОМПАС.

+ visual loop / var / properties (Habr + MCP)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from .code_fix import (
    check_task_feature_requirements,
    must_fix_holes,
    normalize_code,
)
from .critic import (
    extract_part_calls,
    review_structure,
    summarize_ops,
    unknown_part_calls,
)
from .templates import try_template
from .validate import validate_generated_code, critic_warnings
from .verify import offline_verify_report


def analyze(task: str, code: str) -> Dict[str, Any]:
    code = normalize_code(code)
    ok_syn, syn_err = validate_generated_code(code)
    missing = check_task_feature_requirements(task, code)
    structural = review_structure(task, code)
    calls = extract_part_calls(code)
    unknown = unknown_part_calls(code)
    ops = summarize_ops(code)
    soft = critic_warnings(code, task)
    vrep = offline_verify_report(task, code)

    issues: List[str] = []
    if not ok_syn:
        issues.extend(syn_err)
    if must_fix_holes(code):
        issues.append("отверстия без cut/hole")
    if missing:
        issues.append("не хватает по ТЗ: " + ", ".join(missing))
    issues.extend(structural)
    issues.extend(vrep.get("hard_issues") or [])

    timeline = []
    for line in code.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if "part." in s or "sk." in s or "Part.create" in s:
            timeline.append(s)

    return {
        "ok": len(issues) == 0,
        "issues": list(dict.fromkeys(issues)),
        "soft_warnings": soft,
        "verify": vrep,
        "part_calls": calls,
        "unknown_methods": unknown,
        "ops_count": ops,
        "timeline": timeline,
        "code_lines": len([ln for ln in code.splitlines() if ln.strip()]),
    }


def format_report(task: str, code: str, result: Dict[str, Any]) -> str:
    lines = [
        "=== dry-run (без КОМПАС) ===",
        f"ТЗ: {task[:200]}{'…' if len(task) > 200 else ''}",
        f"Строк кода: {result['code_lines']}",
        f"Вызовы part: {', '.join(result['part_calls']) or '—'}",
        f"Route: {result.get('verify', {}).get('route', '—')}",
    ]
    if result["unknown_methods"]:
        lines.append("⚠ неизвестные методы: " + ", ".join(result["unknown_methods"]))
    lines.append("Счётчики: " + json.dumps(result["ops_count"], ensure_ascii=False))
    checks = (result.get("verify") or {}).get("checks") or {}
    if checks:
        lines.append(
            "Verify: "
            + ", ".join(f"{k}={'✓' if v else '✗'}" for k, v in checks.items())
        )
    lines.append("")
    lines.append("Последовательность команд:")
    for i, cmd in enumerate(result["timeline"], 1):
        lines.append(f"  {i:02d}. {cmd}")
    lines.append("")
    if result.get("soft_warnings"):
        lines.append("Мягкие (Habr/MCP):")
        for w in result["soft_warnings"]:
            lines.append(f"  ⚠ {w}")
        lines.append("")
    if result["ok"]:
        lines.append("OK — структура допустима (КОМПАС не запускался).")
        if result.get("soft_warnings"):
            lines.append("Рекомендация: добавить var/properties/screenshot перед live.")
    else:
        lines.append("FAIL:")
        for e in result["issues"]:
            lines.append(f"  • {e}")
    return "\n".join(lines)


def _self_test() -> int:
    cases = [
        (
            "Втулка наружный 40 внутренний 20 длина 50",
            """
from core import Part
part = Part.create("Втулка")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)
part.extrude(sk, depth=50)
part.hole(0, 0, diameter=20, through_all=True)
part.update()
""",
            True,
        ),
        (
            "Пробка ступенчатая Ø50 и Ø30",
            """
from core import Part
part = Part.create("Пробка")
with part.sketch("xy") as sk:
    sk.rectangle(0, 0, 50, 30)
part.extrude(sk, depth=10)
part.update()
""",
            False,
        ),
        (
            "BUILD_PLAN ступени пробка",
            """
from core import Part
part = Part.create("Пробка")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 25)
part.extrude(sk, depth=10)
with part.sketch("xy") as sk2:
    sk2.circle(0, 0, 15)
part.extrude(sk2, depth=20)
part.update()
""",
            True,
        ),
    ]
    failed = 0
    for task, code, expect_ok in cases:
        r = analyze(task, code)
        status = "OK" if r["ok"] == expect_ok else "MISMATCH"
        print(f"[{status}] expect_ok={expect_ok} got={r['ok']} issues={r['issues'][:2]}")
        if r["ok"] != expect_ok:
            failed += 1
    tmpl = try_template("Втулка наружный 40 внутренний 20 длина 50")
    if not tmpl or "hole" not in tmpl:
        print("[FAIL] try_template втулка")
        failed += 1
    else:
        print("[OK] try_template втулка")
    t2 = try_template("BUILD_PLAN\nfeature=step\nпробка Ø50 Ø30")
    if t2 is not None:
        print("[FAIL] сложное ТЗ не должно давать шаблон:", t2[:80])
        failed += 1
    else:
        print("[OK] сложное ТЗ → template None")
    # soft warnings present for bushing without var
    r = analyze(
        "Втулка наружный 40 внутренний 20 длина 50",
        tmpl or "",
    )
    if not r.get("soft_warnings"):
        print("[WARN] ожидались soft_warnings для втулки без var — ок если template уже с var")
    else:
        print("[OK] soft_warnings:", r["soft_warnings"][:2])
    return 1 if failed else 0


def main(argv: Optional[List[str]] = None) -> None:
    p = argparse.ArgumentParser(description="Офлайн-проверка кода core без КОМПАС")
    p.add_argument("--task", default="", help="Текст ТЗ")
    p.add_argument("--code", default="", help="Исходный код")
    p.add_argument("--code-file", default="", help="Файл с кодом")
    p.add_argument("--json", action="store_true", help="Вывод JSON")
    p.add_argument("--self-test", action="store_true", help="Встроенные кейсы")
    p.add_argument(
        "--try-template",
        action="store_true",
        help="Сначала попробовать try_template(task)",
    )
    args = p.parse_args(argv)

    if args.self_test:
        sys.exit(_self_test())

    code = args.code
    if args.code_file:
        code = Path(args.code_file).read_text(encoding="utf-8")
    task = args.task.strip()
    if args.try_template and task:
        tmpl = try_template(task)
        if tmpl:
            code = tmpl
            print("# использован try_template\n")
    if not code.strip():
        print("Нужен --code или --code-file (или --self-test)", file=sys.stderr)
        sys.exit(2)
    if not task:
        task = "(без ТЗ — только синтаксис и методы)"

    result = analyze(task, code)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(format_report(task, code, result))
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
