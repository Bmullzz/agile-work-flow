import os
import tempfile
import unittest
from pathlib import Path

from scripts.llm_client import FakeLLMClient
from scripts.workflow_runner import WorkflowRunner
from scripts.workflow_steps import WORKFLOW_STEPS


EXPECTED_OUTPUT_FILES = [
    "00-intake/00-app-intake.md",
    "01-product/01-product-vision.md",
    "02-technical/02-tech-stack.md",
    "02-technical/03-system-architecture.md",
    "03-discovery/04-user-journeys.md",
    "03-discovery/05-epics.md",
    "04-stories/06-product-user-stories.md",
    "04-stories/07-technical-stories.md",
    "04-stories/08-stories-by-application-layer.md",
    "05-planning/09-dependency-analysis.md",
    "05-planning/10-phased-roadmap.md",
    "06-agent-prompts/11-coding-agent-optimized-stories.md",
    "06-agent-prompts/12-coding-agent-prompts.md",
    "06-agent-prompts/13-project-setup-prompt.md",
    "07-quality/14-qa-validation-plan.md",
    "08-documentation/15-documentation-plan.md",
]


class EndToEndMockWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.tmp_path = Path(self.temp_dir.name)
        self.input_path = self.tmp_path / "input" / "app-idea.md"
        self.output_root = self.tmp_path / "output"
        self.input_path.parent.mkdir(parents=True)
        self.input_path.write_text(
            "# App Idea\n\n"
            "Build a local AI agile workflow tool that reads a Markdown app idea "
            "and generates planning documents for a solo developer.",
            encoding="utf-8",
        )

    def test_full_mock_workflow_generates_expected_markdown_without_api_key(self):
        original_api_key = os.environ.pop("OPENAI_API_KEY", None)
        self.addCleanup(self._restore_api_key, original_api_key)

        runner = WorkflowRunner(
            config={"workflow": {"stop_on_failure": True}, "output": {"overwrite": False}},
            workflow_steps=WORKFLOW_STEPS,
            llm_client=FakeLLMClient(),
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(len(result.completed_step_ids), len(WORKFLOW_STEPS))
        self.assertEqual(result.completed_step_ids, [step.step_id for step in WORKFLOW_STEPS])
        for relative_path in EXPECTED_OUTPUT_FILES:
            with self.subTest(relative_path=relative_path):
                output_file = self.output_root / relative_path
                self.assertTrue(output_file.is_file(), f"Missing output: {relative_path}")
                self.assertTrue(
                    output_file.read_text(encoding="utf-8").startswith("#"),
                    f"Invalid Markdown heading in: {relative_path}",
                )

    def test_full_mock_workflow_is_deterministic(self):
        first_outputs = self._run_full_mock_workflow(self.tmp_path / "first")
        second_outputs = self._run_full_mock_workflow(self.tmp_path / "second")

        self.assertEqual(first_outputs, second_outputs)

    def _run_full_mock_workflow(self, root: Path) -> dict[str, str]:
        input_path = root / "input" / "app-idea.md"
        output_root = root / "output"
        input_path.parent.mkdir(parents=True)
        input_path.write_text(self.input_path.read_text(encoding="utf-8"), encoding="utf-8")

        runner = WorkflowRunner(
            config={"workflow": {"stop_on_failure": True}, "output": {"overwrite": False}},
            workflow_steps=WORKFLOW_STEPS,
            llm_client=FakeLLMClient(),
        )
        runner.run(input_path, output_root)

        return {
            relative_path: (output_root / relative_path).read_text(encoding="utf-8")
            for relative_path in EXPECTED_OUTPUT_FILES
        }

    def _restore_api_key(self, value):
        if value is not None:
            os.environ["OPENAI_API_KEY"] = value


if __name__ == "__main__":
    unittest.main()
