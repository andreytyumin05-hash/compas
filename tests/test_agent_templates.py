import unittest

from agent.templates import try_template


class TryTemplateComplexCoverTest(unittest.TestCase):
    def test_complex_cover_with_boss_pocket_and_pattern(self):
        task = (
            "Крышка stadium 116x80 thickness=13 outer_radius=40 "
            "boss_height=18 boss_radius=30 pocket_depth=8 pocket_diameter=50 "
            "hole_count=4 pcd=60 hole_diameter=8"
        )

        code = try_template(task)

        self.assertIsNotNone(code)
        self.assertIn("part.extrude(sk, depth=13.0)", code)
        self.assertIn("part.extrude(sk2, depth=18.0)", code)
        self.assertIn("part.cut(sk3, depth=8.0, through_all=False)", code)
        self.assertIn("pattern_holes_circular", code)

    def test_real_stadium_cover_task_is_not_misdetected_as_cylinder(self):
        task = (
            "Основание 116x80x13 stadium, центральная бобышка Ø60 h18, "
            "глухой карман Ø50 depth8, 4 отверстия PCD60 Ø8, скругление R2, фаска 1mm"
        )

        code = try_template(task)

        self.assertIsNotNone(code)
        self.assertIn("rounded_rect", code)
        self.assertIn("part.extrude(sk, depth=13.0)", code)
        self.assertIn("part.extrude(sk2, depth=18.0)", code)
        self.assertIn("part.cut(sk3, depth=8.0, through_all=False)", code)
        self.assertIn("pattern_holes_circular", code)


if __name__ == "__main__":
    unittest.main()
