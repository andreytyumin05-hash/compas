import os
import unittest

from agent.runner import Agent


class NoLLMFallbackTest(unittest.TestCase):
    def test_agent_falls_back_to_template_when_no_llm_keys_are_present(self):
        old = {k: os.environ.get(k) for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "OPENROUTER_API_KEY", "LLM_PROVIDER")}
        try:
            for k in old:
                os.environ.pop(k, None)
            code, errors = Agent().generate_checked("Крышка stadium 116x80 thickness=13")
            self.assertTrue(code.strip())
            self.assertEqual(errors, [])
            self.assertIn("from core import Part", code)
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main()
