import argparse
import os
import unittest

from run_workflow import (
    create_generation_backend,
    normalize_backend_name,
    selected_backend_name,
)
from scripts.backends.base import GenerationBackendError
from scripts.backends.codex_backend import CodexBackend
from scripts.backends.manual_chatgpt_backend import ManualChatGPTBackend
from scripts.backends.mock_backend import MockGenerationBackend


class BackendSelectionTests(unittest.TestCase):
    def setUp(self):
        self.original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key)

    def test_config_backend_selection(self):
        args = argparse.Namespace(mock_llm=False, backend=None)

        backend = create_generation_backend(args, {"generation": {"backend": "mock"}})

        self.assertIsInstance(backend, MockGenerationBackend)

    def test_cli_backend_override_wins_over_config(self):
        args = argparse.Namespace(mock_llm=False, backend="mock")

        backend = create_generation_backend(
            args,
            {"generation": {"backend": "openai_api"}},
        )

        self.assertIsInstance(backend, MockGenerationBackend)
        self.assertEqual(
            selected_backend_name(args, {"generation": {"backend": "openai_api"}}),
            "mock",
        )

    def test_unsupported_backend_fails_clearly(self):
        args = argparse.Namespace(mock_llm=False, backend="missing")

        with self.assertRaises(GenerationBackendError) as error:
            create_generation_backend(args, {})

        self.assertIn("Unknown generation backend", str(error.exception))

    def test_disabled_backend_fails_clearly(self):
        args = argparse.Namespace(mock_llm=False, backend=None)

        with self.assertRaises(GenerationBackendError) as error:
            create_generation_backend(
                args,
                {
                    "generation": {"backend": "mock"},
                    "backends": {"mock": {"enabled": False}},
                },
            )

        self.assertIn("disabled", str(error.exception))

    def test_backend_aliases_normalize(self):
        self.assertEqual(normalize_backend_name("openai-api"), "openai_api")
        self.assertEqual(normalize_backend_name("manual-chatgpt"), "manual_chatgpt")
        self.assertEqual(normalize_backend_name("codex"), "codex")
        self.assertEqual(normalize_backend_name("mock"), "mock")

    def test_missing_api_key_is_only_required_for_openai_api(self):
        args = argparse.Namespace(mock_llm=False, backend=None)

        for backend_name, expected_type in (
            ("manual_chatgpt", ManualChatGPTBackend),
            ("codex", CodexBackend),
            ("mock", MockGenerationBackend),
        ):
            backend = create_generation_backend(
                args,
                {"generation": {"backend": backend_name}},
            )
            self.assertIsInstance(backend, expected_type)

        with self.assertRaises(GenerationBackendError) as error:
            create_generation_backend(args, {"generation": {"backend": "openai_api"}})

        self.assertIn("OPENAI_API_KEY is not configured", str(error.exception))

    def test_backend_specific_config_is_used(self):
        args = argparse.Namespace(mock_llm=False, backend="manual-chatgpt")

        backend = create_generation_backend(
            args,
            {
                "backends": {
                    "manual_chatgpt": {
                        "enabled": True,
                        "prompt_export_dir": "custom/prompts",
                        "response_import_dir": "custom/responses",
                    }
                }
            },
        )

        self.assertEqual(str(backend.prompt_directory), "custom/prompts")
        self.assertEqual(str(backend.response_directory), "custom/responses")

    def _restore_api_key(self):
        os.environ.pop("OPENAI_API_KEY", None)
        if self.original_api_key is not None:
            os.environ["OPENAI_API_KEY"] = self.original_api_key


if __name__ == "__main__":
    unittest.main()
