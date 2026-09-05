import unittest

from agent.validate import critic_warnings, validate_generated_code


class VisualAndVarsTest(unittest.TestCase):
    def test_code_with_param_ok(self):
        code = (
            "from core import Part\n"
            "part = Part.create('Втулка')\n"
            "part.param('D', 40)\n"
            "part.param('d', 20)\n"
            "part.param('L', 50)\n"
            "with part.sketch('xy') as sk:\n"
            "    sk.circle(0, 0, part.p('D') / 2)\n"
            "part.extrude(sk, depth=part.p('L'))\n"
            "part.hole(0, 0, diameter=part.p('d'), through_all=True)\n"
            "part.update()\n"
        )
        ok, err = validate_generated_code(code)
        self.assertTrue(ok, err)
        w = critic_warnings(code, "Втулка 40 20 50")
        self.assertFalse(any("param" in x for x in w), w)

    def test_critic_warns_without_param(self):
        code = (
            "from core import Part\n"
            "part = Part.create('X')\n"
            "with part.sketch('xy') as sk:\n"
            "    sk.circle(0, 0, 20)\n"
            "part.extrude(sk, depth=50)\n"
            "part.update()\n"
        )
        w = critic_warnings(code, "Втулка наружный 40 внутренний 20 длина 50")
        self.assertTrue(any("param" in x for x in w), w)

    def test_screenshot_without_path_still_parses(self):
        code = (
            "from core import Part\n"
            "part = Part.create('X')\n"
            "with part.sketch('xy') as sk:\n"
            "    sk.circle(0, 0, 10)\n"
            "part.extrude(sk, depth=5)\n"
            "part.update()\n"
        )
        ok, err = validate_generated_code(code)
        self.assertTrue(ok, err)


if __name__ == "__main__":
    unittest.main()
