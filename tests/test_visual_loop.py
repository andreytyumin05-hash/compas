"""Offline tests for visual loop helpers."""

import unittest

from agent.build import _ensure_visual_tail
from agent.visual_critic import _parse, review_screenshots
from agent.templates import try_template


class VisualLoopTest(unittest.TestCase):
    def test_ensure_visual_tail_adds_screenshots(self):
        code = (
            "from core import Part\n"
            "part = Part.create('X')\n"
            "with part.sketch('xy') as sk:\n"
            "    sk.circle(0,0,10)\n"
            "part.extrude(sk, depth=5)\n"
            "part.update()\n"
        )
        out = _ensure_visual_tail(code)
        self.assertIn("screenshot", out)
        self.assertIn("set_view", out)

    def test_ensure_skips_if_already_present(self):
        code = (
            "from core import Part\n"
            "part = Part.create('X')\n"
            "part.update()\n"
            "part.screenshot('a.png')\n"
        )
        self.assertEqual(_ensure_visual_tail(code), code)

    def test_parse_critic_json(self):
        d = _parse('{"ok": false, "issues": ["нет отверстия"]}')
        self.assertFalse(d["ok"])
        self.assertIn("отверстия", d["issues"][0])

    def test_review_no_images_empty(self):
        self.assertEqual(review_screenshots("тз", "code", []), [])

    def test_bushing_template_has_param_and_dim(self):
        code = try_template("Втулка наружный 40 внутренний 20 длина 50")
        self.assertIsNotNone(code)
        self.assertIn("part.param", code)
        self.assertIn("part.p(", code)
        self.assertIn("dim_radial", code)


if __name__ == "__main__":
    unittest.main()
