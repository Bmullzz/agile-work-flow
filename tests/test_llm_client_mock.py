import os
import unittest

from scripts.llm_client import FakeLLMClient


class FakeLLMClientTests(unittest.TestCase):
    def test_fake_client_returns_string(self):
        result = FakeLLMClient().generate("some prompt")

        self.assertIsInstance(result, str)

    def test_fake_output_starts_with_heading(self):
        result = FakeLLMClient().generate("some prompt")

        self.assertTrue(result.startswith("#"))

    def test_fake_client_requires_no_api_key(self):
        original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key, original_api_key)

        result = FakeLLMClient().generate("some prompt")

        self.assertIn("FakeLLMClient", result)

    def test_fake_client_can_be_injected_into_runner_like_callable(self):
        def run_one_prompt(prompt: str, llm_client) -> str:
            return llm_client.generate(prompt)

        result = run_one_prompt("Build a workflow tool", FakeLLMClient())

        self.assertIn("Build a workflow tool", result)

    def test_empty_prompt_returns_clear_fake_markdown(self):
        result = FakeLLMClient().generate("")

        self.assertIn("(empty prompt)", result)

    def test_none_prompt_fails_clearly(self):
        with self.assertRaises(ValueError) as error:
            FakeLLMClient().generate(None)

        self.assertIn("Prompt cannot be None", str(error.exception))

    def _restore_api_key(self, value):
        if value is not None:
            os.environ["OPENAI_API_KEY"] = value


if __name__ == "__main__":
    unittest.main()
