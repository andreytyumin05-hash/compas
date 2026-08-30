import unittest

from agent.code_fix import check_task_feature_requirements


class TaskFeatureRequirementsTest(unittest.TestCase):
    def test_missing_pocket_and_fillet_are_reported(self):
        task = (
            "Основание 100x60x8, центральная бобышка 20mm, глухой карман глубиной 6, "
            "отверстия по PCD 50 count 4 diameter 8, скругление 2mm"
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

        self.assertIn("pocket", " ".join(missing))
        self.assertIn("fillet", " ".join(missing))

    def test_step_and_slot_are_detected_as_required_features(self):
        task = "Плита 120x80x10, уступ с шириной 20 высотой 12, продольный паз 6мм по центру"
        code = """
from core import Part
part = Part.create('Деталь')
with part.sketch('xy') as sk:
    sk.rectangle(0, 0, 120, 80)
part.extrude(sk, depth=10)
part.update()
"""

        missing = check_task_feature_requirements(task, code)

        self.assertIn("step", " ".join(missing))
        self.assertIn("slot", " ".join(missing))

    def test_valid_complex_cover_does_not_trip_false_feature_blockers(self):
        task = (
            "Крышка stadium 116x80 thickness=13, бобышка Ø30, карман Ø50 depth8, "
            "отверстия 6xØ7, скругление R2, фаска 1mm, feature_tree"
        )
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
part.fillet(radius=2)
part.chamfer(size=1)
part.update()
"""

        missing = check_task_feature_requirements(task, code)

        self.assertNotIn("feature_tree", " ".join(missing))
        self.assertNotIn("pocket", " ".join(missing))
        self.assertNotIn("hole", " ".join(missing))
        self.assertNotIn("fillet", " ".join(missing))
        self.assertNotIn("chamfer", " ".join(missing))

    def test_shell_and_thread_are_safe_fallbacks(self):
        from core import Part

        part = Part.create('Тест')
        part.shell(thickness=1.5)
        part.thread(x=0, y=0, diameter=8, pitch=1.5, length=10)
        part.update()


if __name__ == "__main__":
    unittest.main()
