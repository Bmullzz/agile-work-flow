import argparse
import os
import tempfile
import unittest
from pathlib import Path

from run_workflow import create_generation_backend
from scripts.backends.base import GenerationBackend, GenerationBackendError
from scripts.backends.manual_chatgpt_backend import ManualChatGPTBackend
from scripts.backends.mock_backend import MockGenerationBackend
from scripts.models import WorkflowStep
from scripts.workflow_runner import WorkflowRunner


class RecordingBackend(GenerationBackend):
    def __init__(self):
        self.calls = []

    def generate(self, step, prompt, context):
        self.calls.append({"step": step, "prompt": prompt, "context": context})
        return "# Generated\n\nContent"


class GenerationBackendTests(unittest.TestCase):
    def test_mock_backend_returns_deterministic_markdown(self):
        step = WorkflowStep(
            step_number=0,
            step_id="00-test",
            name="Test",
            prompt_template_path="unused.md",
            output_path="00-test.md",
            required_sections=["Overview"],
        )
        backend = MockGenerationBackend()

        first = backend.generate(step=step, prompt="Build a tool", context={})
        second = backend.generate(step=step, prompt="Build a tool", context={})

        self.assertEqual(first, second)
        self.assertTrue(first.startswith("#"))
        self.assertIn("## Overview", first)

    def test_runner_uses_generation_backend_interface(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_path = root / "input" / "app-idea.md"
            output_root = root / "output"
            input_path.parent.mkdir()
            input_path.write_text(
                "# App Idea\n\n"
                "Build a useful local workflow planning application for solo "
                "developers who need generated product and technical planning documents.",
                encoding="utf-8",
            )
            step = WorkflowStep(
                step_number=0,
                step_id="00-test",
                name="Test",
                prompt_template_path="unused.md",
                output_path="00-test.md",
            )
            backend = RecordingBackend()
            runner = WorkflowRunner(
                config={},
                workflow_steps=[step],
                prompt_loader=lambda path, context: "# Rendered Prompt",
                context_builder=lambda step, input_path, output_root, completed_steps: {
                    "APP_IDEA": "idea"
                },
                generation_backend=backend,
            )

            runner.run(input_path, output_root)

            self.assertEqual(len(backend.calls), 1)
            self.assertIs(backend.calls[0]["step"], step)
            self.assertEqual(backend.calls[0]["prompt"], "# Rendered Prompt")
            self.assertEqual(backend.calls[0]["context"]["APP_IDEA"], "idea")
            self.assertEqual(
                backend.calls[0]["context"]["OUTPUT_ROOT"],
                str(output_root),
            )
            self.assertTrue(
                backend.calls[0]["context"]["PENDING_PROMPT_PATH"].endswith(
                    "99-meta/pending-prompts/00-test.prompt.md"
                )
            )
            self.assertTrue(
                backend.calls[0]["context"]["MANUAL_RESPONSE_PATH"].endswith(
                    "99-meta/manual-responses/00-test.response.md"
                )
            )

    def test_unknown_backend_configuration_fails_clearly(self):
        args = argparse.Namespace(mock_llm=False)

        with self.assertRaises(GenerationBackendError) as error:
            create_generation_backend(
                args,
                {"generation": {"backend": "missing_backend"}},
            )

        self.assertIn("Unknown generation backend", str(error.exception))

    def test_mock_flag_selects_mock_backend_without_api_key(self):
        original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key, original_api_key)
        args = argparse.Namespace(mock_llm=True)

        backend = create_generation_backend(args, {"generation": {"backend": "openai_api"}})

        self.assertIsInstance(backend, MockGenerationBackend)

    def test_manual_chatgpt_backend_can_be_selected_without_api_key(self):
        original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key, original_api_key)
        args = argparse.Namespace(mock_llm=False)

        backend = create_generation_backend(
            args,
            {"generation": {"backend": "manual_chatgpt"}},
        )

        self.assertIsInstance(backend, ManualChatGPTBackend)

    def _restore_api_key(self, value):
        if value is not None:
            os.environ["OPENAI_API_KEY"] = value


if __name__ == "__main__":
    unittest.main()
