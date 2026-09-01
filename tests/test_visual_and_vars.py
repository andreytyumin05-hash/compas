"""Offline-тесты Visual Fluent v2 (без КОМПАС)."""

import unittest

from agent.validate import validate_generated_code, critic_warnings
from agent.critic import unknown_part_calls, KNOWN_PART_METHODS


class VisualAndVarsTest(unittest.TestCase):
    def test_code_with_var_and_screenshot_valid(self):
        code = '''
from core import Part
part = Part.create("Втулка")
part.var("D", 40)
part.var("d", 20)
part.var("L", 50)
part.set_properties(name="Втулка", designation="Bushing")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)
part.extrude(sk, depth=50)
part.hole(0, 0, diameter=20, through_all=True)
part.set_view("iso")
part.screenshot("out/preview.png")
part.update()
'''
        ok, err = validate_generated_code(code)
        self.assertTrue(ok, err)
        self.assertEqual(unknown_part_calls(code), [])
        self.assertEqual(critic_warnings(code, "Втулка 40 20 50"), [])

    def test_critic_warns_without_var(self):
        code = '''
from core import Part
part = Part.create("Втулка")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 20)
part.extrude(sk, depth=50)
part.hole(0, 0, diameter=20, through_all=True)
part.update()
'''
        w = critic_warnings(code, "Втулка наружный 40 внутренний 20 длина 50")
        self.assertTrue(any("var" in x for x in w), w)

    def test_known_methods_include_fluent(self):
        for m in ("var", "set_properties", "get_context", "set_view", "screenshot"):
            self.assertIn(m, KNOWN_PART_METHODS, m)

    def test_screenshot_without_path_still_parses(self):
        # validate only syntax / imports
        code = '''
from core import Part
part = Part.create("X")
with part.sketch("xy") as sk:
    sk.circle(0, 0, 10)
part.extrude(sk, depth=5)
part.update()
'''
        ok, err = validate_generated_code(code)
        self.assertTrue(ok, err)


if __name__ == "__main__":
    unittest.main()
