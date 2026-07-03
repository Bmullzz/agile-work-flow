import os
import tempfile
import unittest
from pathlib import Path

from scripts.models import WorkflowStep
from scripts.workflow_runner import WorkflowRunError, WorkflowRunner
from scripts.workflow_state import load_state


class FailingLLMClient:
    def __init__(self, error_message: str = "provider failed"):
        self.error_message = error_message

    def generate(self, prompt: str) -> str:
        raise RuntimeError(self.error_message)


class ErrorHandlingTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.input_path = self.root / "input" / "app-idea.md"
        self.output_root = self.root / "output"
        self.input_path.parent.mkdir()
        self.input_path.write_text(
            "# App Idea\n\nBuild a local AI workflow tool that creates planning documents.",
            encoding="utf-8",
        )
        self.step = WorkflowStep(
            step_number=0,
            step_id="00-first",
            name="First",
            prompt_template_path=Path("unused.md"),
            output_path=Path("00-first.md"),
        )

    def test_failure_event_is_logged(self):
        runner = WorkflowRunner(
            config={"workflow": {"stop_on_failure": True}},
            workflow_steps=[self.step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=FailingLLMClient("provider failed"),
        )

        with self.assertRaises(WorkflowRunError):
            runner.run(self.input_path, self.output_root)

        log_content = self._read_log()
        self.assertIn("workflow_start", log_content)
        self.assertIn("step_start step=00-first", log_content)
        self.assertIn("step_failure step=00-first", log_content)
        self.assertIn("workflow_failure step=00-first", log_content)

    def test_failure_updates_state(self):
        runner = WorkflowRunner(
            config={"workflow": {"stop_on_failure": True}},
            workflow_steps=[self.step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=FailingLLMClient("provider failed"),
        )

        with self.assertRaises(WorkflowRunError):
            runner.run(self.input_path, self.output_root)

        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.workflow_status, "failed")
        self.assertEqual(state.failed_step, "00-first")

    def test_secrets_are_not_logged_on_failure(self):
        original_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "secret-test-key"
        self.addCleanup(self._restore_api_key, original_key)
        runner = WorkflowRunner(
            config={"workflow": {"stop_on_failure": True}},
            workflow_steps=[self.step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=FailingLLMClient("provider failed secret-test-key"),
        )

        with self.assertRaises(WorkflowRunError):
            runner.run(self.input_path, self.output_root)

        log_content = self._read_log()
        self.assertNotIn("secret-test-key", log_content)
        self.assertIn("[redacted]", log_content)

    def _read_log(self) -> str:
        return (self.output_root / "logs" / "workflow.log").read_text(encoding="utf-8")

    def _restore_api_key(self, value):
        os.environ.pop("OPENAI_API_KEY", None)
        if value is not None:
            os.environ["OPENAI_API_KEY"] = value


if __name__ == "__main__":
    unittest.main()
