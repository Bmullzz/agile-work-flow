import tempfile
import unittest
from pathlib import Path

from scripts.codex_task_writer import CodexTaskWriter
from scripts.models import WorkflowStep


class CodexTaskWriterTests(unittest.TestCase):
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
            depends_on_step_ids=["02-tech-stack"],
            required_sections=["Architecture Overview", "Components"],
        )
        self.context = {
            "APP_IDEA": "Build a local workflow planning tool.",
            "TECH_STACK": "# Tech Stack\n\nUse Python.",
            "WORKFLOW_STATE_SUMMARY": "Current step: 03-system-architecture",
        }
        self.writer = CodexTaskWriter()

    def test_task_packet_creates_expected_files(self):
        result = self.writer.write_task_packet(
            self.output_root,
            self.step,
            "# Rendered Prompt",
            self.context,
            self.output_root / self.step.output_path,
        )

        self.assertEqual(
            result.task_directory,
            self.output_root / "99-meta/codex-tasks/03-system-architecture",
        )
        for path in (
            result.prompt_path,
            result.context_path,
            result.expected_output_path,
            result.target_file_path,
            result.instructions_path,
        ):
            self.assertTrue(path.is_file(), path)

    def test_task_files_include_step_id_and_name(self):
        result = self.writer.write_task_packet(
            self.output_root,
            self.step,
            "# Rendered Prompt",
            self.context,
            self.output_root / self.step.output_path,
        )

        prompt_text = result.prompt_path.read_text(encoding="utf-8")
        instructions_text = result.instructions_path.read_text(encoding="utf-8")

        self.assertIn("03-system-architecture", prompt_text)
        self.assertIn("System Architecture", prompt_text)
        self.assertIn("03-system-architecture", instructions_text)
        self.assertIn("System Architecture", instructions_text)

    def test_target_file_path_is_written(self):
        target_path = self.output_root / self.step.output_path

        result = self.writer.write_task_packet(
            self.output_root,
            self.step,
            "# Rendered Prompt",
            self.context,
            target_path,
        )

        self.assertEqual(
            result.target_file_path.read_text(encoding="utf-8").strip(),
            str(target_path),
        )

    def test_context_includes_dependency_outputs(self):
        result = self.writer.write_task_packet(
            self.output_root,
            self.step,
            "# Rendered Prompt",
            self.context,
            self.output_root / self.step.output_path,
        )

        context_text = result.context_path.read_text(encoding="utf-8")

        self.assertIn("Build a local workflow planning tool.", context_text)
        self.assertIn("## Dependency Outputs", context_text)
        self.assertIn("# Tech Stack", context_text)
        self.assertIn("Current step: 03-system-architecture", context_text)

    def test_task_export_protects_existing_files_by_default(self):
        self.writer.write_task_packet(
            self.output_root,
            self.step,
            "# Rendered Prompt",
            self.context,
            self.output_root / self.step.output_path,
        )

        with self.assertRaises(FileExistsError):
            self.writer.write_task_packet(
                self.output_root,
                self.step,
                "# Updated Prompt",
                self.context,
                self.output_root / self.step.output_path,
            )

    def test_overwrite_replaces_existing_task_files(self):
        self.writer.write_task_packet(
            self.output_root,
            self.step,
            "# Rendered Prompt",
            self.context,
            self.output_root / self.step.output_path,
        )

        result = self.writer.write_task_packet(
            self.output_root,
            self.step,
            "# Updated Prompt",
            self.context,
            self.output_root / self.step.output_path,
            overwrite=True,
        )

        self.assertIn(
            "# Updated Prompt",
            result.prompt_path.read_text(encoding="utf-8"),
        )


if __name__ == "__main__":
    unittest.main()
