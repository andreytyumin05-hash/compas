"""Ложные срабатывания покрытия фич."""

import unittest

from agent.code_fix import check_task_feature_requirements
from agent.schema import spec_to_task_text
from agent.dry_run import analyze


class FeatureFalsePositivesTest(unittest.TestCase):
    def test_order_boilerplate_does_not_require_pocket(self):
        task = spec_to_task_text(
            {
                "part_type": "plate",
                "name": "Плита",
                "overall": {"length": 100, "width": 60, "thickness": 8},
                "features": [{"type": "extrude_body", "params": {"length": 100, "width": 60, "thickness": 8}}],
            }
        )
        code = """
from core import Part
part = Part.create("Плита")
with part.sketch("xy") as sk:
    sk.rectangle(-50, -30, 100, 60)
part.extrude(sk, depth=8)
part.update()
"""
        missing = check_task_feature_requirements(task, code)
        self.assertNotIn("pocket", missing)
        self.assertNotIn("hole", missing)
        self.assertNotIn("chamfer", missing)

    def test_groove_required_when_feature_groove(self):
        task = "feature=groove\nouter_diameter=42\ninner_diameter=36\ndepth=2"
        code = """
from core import Part
part = Part.create("X")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 25)
part.extrude(sk, depth=20)
part.update()
"""
        missing = check_task_feature_requirements(task, code)
        self.assertIn("groove", missing)

    def test_plug_good_code_ok(self):
        task = spec_to_task_text(
            {
                "part_type": "plug",
                "name": "Пробка",
                "build_plan": ["1. Ø50", "2. Ø42"],
                "features": [
                    {"type": "extrude_body", "params": {"diameter": 50, "length": 10}},
                    {"type": "step", "params": {"diameter": 42, "length": 20}},
                ],
                "overall": {},
            }
        )
        code = """
from core import Part
part = Part.create("Пробка")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 25)
part.extrude(sk, depth=10)
with part.sketch("xy") as sk2:
    sk2.circle(0, 0, 21)
part.extrude(sk2, depth=20)
part.update()
"""
        r = analyze(task, code)
        self.assertTrue(r["ok"], r["issues"])


if __name__ == "__main__":
    unittest.main()
