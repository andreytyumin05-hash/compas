"""Шаблоны: только простые кейсы; сложные → None."""

import unittest

from agent.templates import try_template


class TryTemplateTest(unittest.TestCase):
    def test_simple_bushing(self):
        code = try_template("Втулка наружный 40 внутренний 20 длина 50")
        self.assertIsNotNone(code)
        self.assertIn("circle",
                      code)
        self.assertIn("hole(", code)

    def test_complex_cover_goes_to_llm(self):
        task = (
            "Крышка stadium 116x80 thickness=13 boss_height=18 "
            "pocket_depth=8 feature=step BUILD_PLAN"
        )
        self.assertIsNone(try_template(task))

    def test_plug_steps_no_template(self):
        self.assertIsNone(
            try_template("Пробка ступень Ø50 длина 10 ступень Ø36 длина 20")
        )

    def test_ocr_complex_no_cylinder_template(self):
        task = (
            "Распознал так: Крышка габарит 116x80 бобышка отверстия "
            "feature=boss feature=pattern_holes"
        )
        # либо None, либо не «Цилиндр»
        code = try_template(task)
        if code:
            self.assertNotIn('Part.create("Цилиндр")', code)


if __name__ == "__main__":
    unittest.main()
