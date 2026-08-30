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

    def test_step_and_slot_template_uses_expanded_features(self):
        task = "Плита 120x80x10, уступ шириной 20 высотой 12, продольный паз 6 по центру"

        code = try_template(task)

        self.assertIsNotNone(code)
        self.assertIn("part.step(", code)
        self.assertIn("part.slot(", code)

    def test_complex_cover_example_from_answers_is_supported(self):
        task = (
            "Крышка stadium 116x80 thickness=13 overall_height=31, "
            "бобышка центральная R21, два основных отверстия Ø28, "
            "6 крепежных отверстий Ø7 с цековкой Ø11 глубиной 6, "
            "2 штифтовых отверстия Ø5, скругление R2, фаска 1mm"
        )

        code = try_template(task)

        self.assertIsNotNone(code)
        self.assertIn("rounded_rect", code)
        self.assertIn("part.extrude(sk, depth=13.0)", code)
        self.assertIn("part.pattern_holes_circular", code)
        self.assertIn("part.cut(sk3", code)
        self.assertIn("part.fillet", code)
        self.assertIn("part.chamfer", code)

    def test_ocr_like_cover_text_is_not_misclassified_as_cylinder(self):
        task = (
            "Распознал так:\n"
            "Деталь: Крышка (крышка)\n"
            "Размеры: габарит 116?80 mm; толщина 13 mm; общая высота 31 mm\n"
            "Основной фланец овальной (стадионной) формы R40\n"
            "бобышка / выступ: R21 мм\n"
            "группа отверстий: O28 мм, кол-во 2 мм, сквозное\n"
            "группа отверстий: O7 мм, кол-во 6 мм, сквозное, 6 крепежных отверстий o7 с цековкой o11 глубиной 6 мм\n"
            "группа отверстий: O5 мм, кол-во 2 мм, сквозное"
        )

        code = try_template(task)

        self.assertIsNotNone(code)
        self.assertIn("rounded_rect", code)
        self.assertIn("part.pattern_holes_circular", code)
        self.assertNotIn('Part.create("Цилиндр")', code)


if __name__ == "__main__":
    unittest.main()
