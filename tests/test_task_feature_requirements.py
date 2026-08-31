import unittest

from agent.code_fix import check_task_feature_requirements


class TaskFeatureRequirementsTest(unittest.TestCase):
    def test_missing_pocket_and_fillet(self):
        task = (
            "Основание 100x60x8, бобышка, глухой карман глубиной 6, "
            "отверстия PCD, скругление 2mm"
        )
        code = """
from core import Part
part = Part.create('Деталь')
with part.sketch('xy') as sk:
    sk.rectangle(0, 0, 100, 60)
part.extrude(sk, depth=8)
with part.sketch('xy') as sk2:
    sk2.circle(0, 0, 10)
part.extrude(sk2, depth=20)
part.pattern_holes_circular((0, 0), pcd=50, count=4, diameter=8)
part.update()
"""
        missing = check_task_feature_requirements(task, code)
        joined = " ".join(missing)
        self.assertIn("pocket", joined)
        self.assertIn("fillet", joined)

    def test_slot_required(self):
        task = "Плита 120x80x10, продольный паз 6мм"
        code = """
from core import Part
part = Part.create('Деталь')
with part.sketch('xy') as sk:
    sk.rectangle(0, 0, 120, 80)
part.extrude(sk, depth=10)
part.update()
"""
        missing = check_task_feature_requirements(task, code)
        self.assertIn("slot", " ".join(missing))

    def test_full_cover_ok(self):
        task = "Крышка карман depth8 отверстия скругление фаска"
        code = """
from core import Part
part = Part.create('Деталь')
with part.sketch('xy') as sk:
    sk.rounded_rect(-58, -40, 116, 80, radius=40)
part.extrude(sk, depth=13)
with part.sketch('xy') as sk2:
    sk2.circle(0, 0, 15)
part.extrude(sk2, depth=18)
with part.sketch('xy') as sk3:
    sk3.circle(0, 0, 25)
part.cut(sk3, depth=8, through_all=False)
part.pattern_holes_circular((0, 0), pcd=60, count=6, diameter=7)
edges = part.get_edges("all")
part.fillet(edges, radius=2)
part.chamfer(edges, distance=1)
part.update()
"""
        missing = check_task_feature_requirements(task, code)
        self.assertEqual(missing, [])


if __name__ == "__main__":
    unittest.main()
