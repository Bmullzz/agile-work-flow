import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from scripts.backends.base import GenerationBackendError
from scripts.backends.openai_api_backend import OpenAIAPIBackend
from scripts.logger import setup_workflow_logging
from scripts.models import WorkflowStep


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


class OpenAIAPIBackendTests(unittest.TestCase):
    def setUp(self):
        self.original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key)
        self.step = WorkflowStep(
            step_number=0,
            step_id="00-test",
            name="Test",
            prompt_template_path="unused.md",
            output_path="00-test.md",
        )

    def test_missing_api_key_fails_clearly(self):
        with self.assertRaises(GenerationBackendError) as error:
            OpenAIAPIBackend(
                config={"generation": {"backend": "openai_api"}},
                openai_client=FakeOpenAIProvider(),
                env_loader=lambda: None,
            )

        self.assertIn("OPENAI_API_KEY is not configured", str(error.exception))

    def test_config_driven_model_selection(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = FakeOpenAIProvider()
        backend = OpenAIAPIBackend(
            config={
                "backends": {
                    "openai_api": {
                        "model": "backend-model",
                        "temperature": 0.4,
                        "timeout_seconds": 12,
                        "max_retries": 0,
                    }
                }
            },
            openai_client=provider,
            env_loader=lambda: None,
        )

        result = backend.generate(
            step=self.step,
            prompt="rendered prompt",
            context={"APP_IDEA": "idea"},
        )

        self.assertTrue(result.startswith("#"))
        self.assertEqual(provider.responses.calls[0]["model"], "backend-model")
        self.assertEqual(provider.responses.calls[0]["temperature"], 0.4)
        self.assertEqual(provider.responses.calls[0]["timeout"], 12)

    def test_provider_error_handling_does_not_log_api_key(self):
        os.environ["OPENAI_API_KEY"] = "secret-test-key"
        provider = FakeOpenAIProvider(error=BadRequestError("bad secret-test-key"))
        backend = OpenAIAPIBackend(
            config={"backends": {"openai_api": {"model": "test-model", "max_retries": 0}}},
            openai_client=provider,
            env_loader=lambda: None,
        )

        with self.assertRaises(GenerationBackendError) as error:
            backend.generate(step=self.step, prompt="rendered prompt", context={})

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
        backend = OpenAIAPIBackend(
            config={
                "backends": {
                    "openai_api": {
                        "model": "test-model",
                        "max_retries": 1,
                        "retry_delay_seconds": 0,
                    }
                }
            },
            openai_client=provider,
            env_loader=lambda: None,
        )

        result = backend.generate(step=self.step, prompt="rendered prompt", context={})

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
            backend = OpenAIAPIBackend(
                config={
                    "backends": {
                        "openai_api": {
                            "model": "test-model",
                            "max_retries": 1,
                            "retry_delay_seconds": 0,
                        }
                    }
                },
                openai_client=provider,
                env_loader=lambda: None,
                logger=logger,
            )

            backend.generate(step=self.step, prompt="rendered prompt", context={})

            self.assertIn("llm_retry", log_path.read_text(encoding="utf-8"))

    def test_empty_provider_response_fails(self):
        os.environ["OPENAI_API_KEY"] = "test-key"
        provider = FakeOpenAIProvider(responses=[SimpleNamespace(output_text="")])
        backend = OpenAIAPIBackend(
            config={"backends": {"openai_api": {"model": "test-model"}}},
            openai_client=provider,
            env_loader=lambda: None,
        )

        with self.assertRaises(GenerationBackendError) as error:
            backend.generate(step=self.step, prompt="rendered prompt", context={})

        self.assertIn("empty response", str(error.exception))

    def _restore_api_key(self):
        os.environ.pop("OPENAI_API_KEY", None)
        if self.original_api_key is not None:
            os.environ["OPENAI_API_KEY"] = self.original_api_key


if __name__ == "__main__":
    unittest.main()
