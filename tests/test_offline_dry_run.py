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
part.param("D_OUT", 40)
part.param("D_IN", 20)
part.param("L", 50)
with part.sketch("xy") as sk:
    sk.circle(0, 0, part.p("D_OUT") / 2)
part.extrude(sk, depth=part.p("L"))
part.hole(0, 0, diameter=part.p("D_IN"), through_all=True)
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

    def test_complex_task_no_box_template(self):
        self.assertIsNone(try_template("Сложная крышка stadium feature=boss"))

    def test_schema_build_plan_in_user_text(self):
        task = spec_to_task_text(
            {
                "part_type": "plug",
                "name": "Пробка",
                "overall": {"outer_diameter": 50},
                "build_plan": ["1. База Ø50", "2. Ступень Ø30"],
                "features": [
                    {"type": "step", "params": {"diameter": 50, "length": 10}, "notes": "голова"}
                ],
            }
        )
        self.assertTrue("RULE: solid_lines=body" in task or "dashed" in task.lower())

    def test_simple_bushing_template(self):
        code = try_template("Втулка наружный 40 внутренний 20 длина 50")
        self.assertIsNotNone(code)
        self.assertIn("part.param", code)

    def test_step_and_slot_are_allowed_methods(self):
        code = (
            "from core import Part\n"
            "part = Part.create('X')\n"
            "with part.sketch('xy') as sk:\n"
            "    sk.rectangle(0,0,10,10)\n"
            "part.extrude(sk, depth=5)\n"
            "part.slot(0,0,10,0,width=3,depth=2)\n"
            "part.step(0,0,width=5,height=2,depth=3)\n"
            "part.update()\n"
        )
        ok, err = validate_generated_code(code)
        self.assertTrue(ok, err)

    def test_unknown_method_flagged(self):
        code = (
            "from core import Part\n"
            "part = Part.create('X')\n"
            "part.not_a_real_method()\n"
            "part.update()\n"
        )
        bad = unknown_part_calls(code)
        self.assertTrue(any("not_a_real" in x for x in bad))


if __name__ == "__main__":
    unittest.main()
