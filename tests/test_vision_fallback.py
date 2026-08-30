import unittest

from bot.__main__ import build_vision_failure_message


class VisionFallbackTest(unittest.TestCase):
    def test_vision_failure_message_prompts_for_text_input(self):
        msg = build_vision_failure_message()
        low = msg.lower()
        self.assertIn("текстом", low)
        self.assertIn("размер", low)
        self.assertIn("чертёж", low)


if __name__ == "__main__":
    unittest.main()
