import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.llm_client import FakeLLMClient, LLMClientError, OpenAILLMClient
from scripts.logger import setup_workflow_logging


class FakeResponses:
    def __init__(self, responses=None, error=None):
        self.calls = []
        self.responses = list(responses or [])
        self.error = error

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
            return response
        return SimpleNamespace(output_text="# Real Markdown\n\nGenerated")


class FakeOpenAIProvider:
    def __init__(self, responses=None, error=None):
        self.responses = FakeResponses(responses=responses, error=error)


class APITimeoutError(Exception):
    pass


class BadRequestError(Exception):
    pass


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


class OpenAILLMClientTests(unittest.TestCase):
    def setUp(self):
        self.original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key)

    def test_missing_api_key_fails_clearly(self):
        with self.assertRaises(LLMClientError) as error:
            OpenAILLMClient(
                config={"llm": {"model": "test-model"}},
                openai_client=FakeOpenAIProvider(),
                env_loader=lambda: None,
            )

        self.assertIn("OPENAI_API_KEY is not configured", str(error.exception))

    def test_config_driven_model_selection(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = FakeOpenAIProvider()
        client = OpenAILLMClient(
            config={
                "llm": {
                    "model": "custom-model",
                    "temperature": 0.4,
                    "timeout_seconds": 12,
                    "max_retries": 0,
                }
            },
            openai_client=provider,
            env_loader=lambda: None,
        )

        result = client.generate("rendered prompt")

        self.assertTrue(result.startswith("#"))
        self.assertEqual(provider.responses.calls[0]["model"], "custom-model")
        self.assertEqual(provider.responses.calls[0]["temperature"], 0.4)
        self.assertEqual(provider.responses.calls[0]["timeout"], 12)

    def test_provider_error_handling_does_not_log_api_key(self):
        os.environ["OPENAI_API_KEY"] = "secret-test-key"
        provider = FakeOpenAIProvider(error=BadRequestError("bad secret-test-key"))
        client = OpenAILLMClient(
            config={"llm": {"model": "test-model", "max_retries": 0}},
            openai_client=provider,
            env_loader=lambda: None,
        )

        with self.assertRaises(LLMClientError) as error:
            client.generate("rendered prompt")

        message = str(error.exception)
        self.assertIn("OpenAI generation failed", message)
        self.assertNotIn("secret-test-key", message)
        self.assertIn("[redacted]", message)

    def test_timeout_retries_before_success(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = FakeOpenAIProvider(
            responses=[
                APITimeoutError("temporary timeout"),
                SimpleNamespace(output_text="# Retried\n\nGenerated"),
            ]
        )
        client = OpenAILLMClient(
            config={
                "llm": {
                    "model": "test-model",
                    "max_retries": 1,
                    "retry_delay_seconds": 0,
                }
            },
            openai_client=provider,
            env_loader=lambda: None,
        )

        result = client.generate("rendered prompt")

        self.assertEqual(result, "# Retried\n\nGenerated")
        self.assertEqual(len(provider.responses.calls), 2)

    def test_timeout_retry_is_logged(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        with tempfile.TemporaryDirectory() as temp_dir:
            logger, log_path = setup_workflow_logging(Path(temp_dir), console=False)
            provider = FakeOpenAIProvider(
                responses=[
                    APITimeoutError("temporary timeout"),
                    SimpleNamespace(output_text="# Retried\n\nGenerated"),
                ]
            )
            client = OpenAILLMClient(
                config={
                    "llm": {
                        "model": "test-model",
                        "max_retries": 1,
                        "retry_delay_seconds": 0,
                    }
                },
                openai_client=provider,
                env_loader=lambda: None,
                logger=logger,
            )

            client.generate("rendered prompt")

            self.assertIn("llm_retry", log_path.read_text(encoding="utf-8"))

    def test_empty_provider_response_fails(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = FakeOpenAIProvider(responses=[SimpleNamespace(output_text="")])
        client = OpenAILLMClient(
            config={"llm": {"model": "test-model"}},
            openai_client=provider,
            env_loader=lambda: None,
        )

        with self.assertRaises(LLMClientError) as error:
            client.generate("rendered prompt")

        self.assertIn("empty response", str(error.exception))

    def _restore_api_key(self):
        os.environ.pop("OPENAI_API_KEY", None)
        if self.original_api_key is not None:
            os.environ["OPENAI_API_KEY"] = self.original_api_key


if __name__ == "__main__":
    unittest.main()
