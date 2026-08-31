"""Офлайн-тесты без КОМПАС и без LLM."""

import unittest

from agent.critic import review_structure, unknown_part_calls
from agent.dry_run import analyze
from agent.templates import try_template
from agent.validate import validate_generated_code
from agent.schema import format_spec_for_user, spec_to_task_text


class OfflineDryRunTest(unittest.TestCase):
    def test_bushing_ok(self):
        task = "Втулка наружный 40 внутренний 20 длина 50"
        code = """
from core import Part
part = Part.create("Втулка")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)
part.extrude(sk, depth=50)
part.hole(0, 0, diameter=20, through_all=True)
part.update()
"""
        r = analyze(task, code)
        self.assertTrue(r["ok"], r["issues"])

    def test_plug_rectangle_rejected(self):
        task = "Пробка ступенчатая Ø50 Ø30"
        code = """
from core import Part
part = Part.create("Пробка")
with part.sketch("xy") as sk:
    sk.rectangle(0, 0, 50, 30)
part.extrude(sk, depth=10)
part.update()
"""
        r = analyze(task, code)
        self.assertFalse(r["ok"])
        self.assertTrue(any("rectangle" in i or "плит" in i for i in r["issues"]))

    def test_unknown_method_flagged(self):
        code = """
from core import Part
part = Part.create("X")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 10)
part.extrude(sk, depth=5)
part.magic_feature(1)
part.update()
"""
        self.assertIn("magic_feature", unknown_part_calls(code))
        issues = review_structure("цилиндр", code)
        self.assertTrue(any("magic" in i for i in issues))

    def test_step_and_slot_are_allowed_methods(self):
        code = """
from core import Part
part = Part.create("Плита")
with part.sketch("xy") as sk:
    sk.rectangle(0, 0, 100, 60)
part.extrude(sk, depth=10)
part.step(0, 0, width=20, height=12, depth=12, shape="rect")
part.slot(-20, 0, 20, 0, width=6, depth=5, through_all=False)
part.update()
"""
        ok, err = validate_generated_code(code)
        self.assertTrue(ok, err)
        self.assertEqual(unknown_part_calls(code), [])
        issues = review_structure("плита уступ паз", code)
        self.assertFalse(any("запрещён" in i for i in issues), issues)

    def test_complex_task_no_box_template(self):
        self.assertIsNone(
            try_template("BUILD_PLAN\nfeature=step\nпробка Ø50 длина 10 Ø30 длина 20")
        )

    def test_simple_bushing_template(self):
        code = try_template("Втулка наружный 40 внутренний 20 длина 50")
        self.assertIsNotNone(code)
        self.assertIn("hole(", code)

    def test_schema_build_plan_in_user_text(self):
        spec = {
            "part_type": "plug",
            "name": "Пробка",
            "units": "mm",
            "overall": {"outer_diameter": 50},
            "build_plan": ["1. База Ø50", "2. Ступень Ø30"],
            "features": [
                {"type": "step", "params": {"diameter": 50, "length": 10}, "notes": "голова"}
            ],
            "drawing": {"dashed_lines": "оси и скрытые отверстия"},
        }
        human = format_spec_for_user(spec)
        self.assertIn("План построения", human)
        task = spec_to_task_text(spec)
        self.assertIn("BUILD_PLAN", task)
        self.assertIn("пунктир", task.lower() + " " + task)


if __name__ == "__main__":
    unittest.main()
