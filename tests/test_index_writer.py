import tempfile
import unittest
from pathlib import Path

from scripts.index_writer import IndexWriter
from scripts.models import WorkflowStep


class IndexWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.output_root = Path(self.temp_dir.name) / "output"
        self.steps = [
            WorkflowStep(
                step_number=0,
                step_id="00-app-intake",
                name="App Intake",
                prompt_template_path="prompts/00-app-intake.md",
                output_path="00-intake/00-app-intake.md",
            ),
            WorkflowStep(
                step_number=12,
                step_id="12-coding-agent-prompts",
                name="Coding-Agent Prompts",
                prompt_template_path="prompts/12-coding-agent-prompts.md",
                output_path="06-agent-prompts/12-coding-agent-prompts.md",
            ),
        ]
        self.write_output(self.steps[0], "# App Intake\n\nContent")
        self.write_output(self.steps[1], "# Coding-Agent Prompts\n\nContent")

    def write_output(self, step: WorkflowStep, content: str) -> None:
        output_path = self.output_root / step.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    def test_readme_creation(self):
        result = IndexWriter().write_indexes(
            self.output_root,
            self.steps,
            run_metadata={"generated_at": "2026-07-03T00:00:00+00:00"},
        )

        self.assertTrue(result.readme_path.is_file())
        readme = result.readme_path.read_text(encoding="utf-8")
        self.assertIn("# AI Agile Workflow Output", readme)
        self.assertTrue(readme.startswith("---\n"))
        self.assertIn('document_id: "README"', readme)
        self.assertIn("Recommended Implementation Path", readme)

    def test_readme_links_to_all_expected_files(self):
        IndexWriter().write_indexes(self.output_root, self.steps)

        readme = (self.output_root / "README.md").read_text(encoding="utf-8")

        self.assertIn("(00-intake/00-app-intake.md)", readme)
        self.assertIn(
            "(06-agent-prompts/12-coding-agent-prompts.md)",
            readme,
        )
        self.assertIn("Coding-Agent Prompts", readme)

    def test_project_context_creation(self):
        result = IndexWriter().write_indexes(self.output_root, self.steps)

        self.assertTrue(result.project_context_path.is_file())
        project_context = result.project_context_path.read_text(encoding="utf-8")
        self.assertIn("# Project Context", project_context)
        self.assertIn('document_id: "project-context"', project_context)
        self.assertIn("00-app-intake", project_context)

    def test_metadata_files_are_generated(self):
        result = IndexWriter().write_indexes(
            self.output_root,
            self.steps,
            run_metadata={
                "workflow_state": {
                    "project_name": "test-project",
                    "workflow_status": "completed",
                    "completed_steps": ["00-app-intake"],
                    "stale_steps": [],
                }
            },
        )

        expected_paths = [
            result.assumptions_path,
            result.open_questions_path,
            result.workflow_state_path,
            result.generation_summary_path,
            result.validation_report_path,
            result.changelog_path,
        ]
        for path in expected_paths:
            self.assertIsNotNone(path)
            self.assertTrue(path.is_file())
            content = path.read_text(encoding="utf-8")
            self.assertTrue(content.startswith("---\n"))
            self.assertIn("#", content)

        workflow_state = result.workflow_state_path.read_text(encoding="utf-8")
        self.assertIn("# Workflow State", workflow_state)
        self.assertIn("Status: completed", workflow_state)

    def test_readme_links_to_metadata_files(self):
        IndexWriter().write_indexes(self.output_root, self.steps)

        readme = (self.output_root / "README.md").read_text(encoding="utf-8")

        self.assertIn("(assumptions.md)", readme)
        self.assertIn("(open-questions.md)", readme)
        self.assertIn("(workflow-state.md)", readme)
        self.assertIn("(99-meta/generation-summary.md)", readme)
        self.assertIn("[[assumptions|Obsidian]]", readme)

    def test_index_generation_with_partial_outputs(self):
        missing_step = WorkflowStep(
            step_number=1,
            step_id="01-product-vision",
            name="Product Vision",
            prompt_template_path="prompts/01-product-vision.md",
            output_path="01-product/01-product-vision.md",
        )

        result = IndexWriter().write_indexes(
            self.output_root,
            self.steps + [missing_step],
        )

        readme = (self.output_root / "README.md").read_text(encoding="utf-8")
        self.assertTrue(result.warnings)
        self.assertIn("Missing optional output skipped", result.warnings[0])
        self.assertNotIn("(01-product/01-product-vision.md)", readme)
        self.assertIn("Warnings", readme)


if __name__ == "__main__":
    unittest.main()
