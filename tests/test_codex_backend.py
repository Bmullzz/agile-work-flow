import os
import tempfile
import unittest
from pathlib import Path

from scripts.backends.base import GenerationBackendError
from scripts.backends.codex_backend import CodexBackend
from scripts.models import WorkflowStep


class CodexBackendTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.output_root = Path(self.temp_dir.name) / "output"
        self.step = WorkflowStep(
            step_number=3,
            step_id="03-system-architecture",
            name="System Architecture",
            prompt_template_path="prompts/03-system-architecture.md",
            output_path="02-technical/03-system-architecture.md",
            required_sections=["Architecture Overview", "Components"],
        )

    def test_generate_exports_task_packet_and_returns_markdown(self):
        backend = CodexBackend()
        target_path = self.output_root / self.step.output_path

        result = backend.generate(
            step=self.step,
            prompt="# Rendered Prompt",
            context={
                "APP_IDEA": "Build a workflow tool.",
                "OUTPUT_ROOT": str(self.output_root),
                "TARGET_OUTPUT_PATH": str(target_path),
            },
        )

        task_dir = self.output_root / "99-meta/codex-tasks/03-system-architecture"
        self.assertTrue(result.startswith("#"))
        self.assertIn("## Architecture Overview", result)
        self.assertIn("## Components", result)
        self.assertTrue((task_dir / "prompt.md").is_file())
        self.assertTrue((task_dir / "context.md").is_file())
        self.assertTrue((task_dir / "expected-output.md").is_file())
        self.assertEqual(
            (task_dir / "target-file.txt").read_text(encoding="utf-8").strip(),
            str(target_path),
        )

    def test_generate_requires_no_api_key(self):
        original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key, original_api_key)

        result = CodexBackend().generate(
            step=self.step,
            prompt="# Rendered Prompt",
            context={
                "APP_IDEA": "Build a workflow tool.",
                "OUTPUT_ROOT": str(self.output_root),
            },
        )

        self.assertIn("Codex Task Exported", result)

    def test_missing_output_root_fails_clearly(self):
        with self.assertRaises(GenerationBackendError) as error:
            CodexBackend().generate(
                step=self.step,
                prompt="# Rendered Prompt",
                context={"APP_IDEA": "Build a workflow tool."},
            )

        self.assertIn("OUTPUT_ROOT", str(error.exception))

    def test_target_output_path_mismatch_fails_validation(self):
        with self.assertRaises(GenerationBackendError) as error:
            CodexBackend().generate(
                step=self.step,
                prompt="# Rendered Prompt",
                context={
                    "APP_IDEA": "Build a workflow tool.",
                    "OUTPUT_ROOT": str(self.output_root),
                    "TARGET_OUTPUT_PATH": str(self.output_root / "wrong.md"),
                },
            )

        self.assertIn("target failed validation", str(error.exception))
        self.assertIn("does not match expected", str(error.exception))

    def test_existing_task_packet_requires_overwrite(self):
        context = {
            "APP_IDEA": "Build a workflow tool.",
            "OUTPUT_ROOT": str(self.output_root),
        }
        backend = CodexBackend()
        backend.generate(step=self.step, prompt="# Rendered Prompt", context=context)

        with self.assertRaises(FileExistsError):
            backend.generate(step=self.step, prompt="# Updated Prompt", context=context)

        updated = backend.generate(
            step=self.step,
            prompt="# Updated Prompt",
            context={**context, "OVERWRITE": True},
        )
        self.assertIn("Codex Task Exported", updated)

    def _restore_api_key(self, value):
        if value is not None:
            os.environ["OPENAI_API_KEY"] = value


if __name__ == "__main__":
    unittest.main()
