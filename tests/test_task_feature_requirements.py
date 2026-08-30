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


if __name__ == "__main__":
    unittest.main()
