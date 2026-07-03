import tempfile
import unittest
from pathlib import Path

from scripts.llm_client import FakeLLMClient
from scripts.models import WorkflowStep
from scripts.workflow_runner import WorkflowRunError, WorkflowRunner
from scripts.workflow_state import load_state
from scripts.workflow_steps import WORKFLOW_STEPS


class RecordingLLMClient:
    def __init__(self, response: str = "# Generated\n\nContent"):
        self.prompts = []
        self.response = response

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class WorkflowRunnerTests(unittest.TestCase):
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

    def make_steps(self):
        return [
            WorkflowStep(
                step_number=0,
                step_id="00-first",
                name="First",
                prompt_template_path=Path("unused-first.md"),
                output_path=Path("00-first.md"),
            ),
            WorkflowStep(
                step_number=1,
                step_id="01-second",
                name="Second",
                prompt_template_path=Path("unused-second.md"),
                output_path=Path("01-second.md"),
                depends_on_step_ids=["00-first"],
            ),
        ]

    def test_runner_executes_steps_in_order(self):
        calls = []

        def prompt_loader(path, context):
            calls.append(("prompt", str(path)))
            return "# Prompt"

        def context_builder(step, input_path, output_root, completed_steps):
            calls.append(("context", step.step_id))
            return {"APP_IDEA": "idea", "PROJECT_CONTEXT": ""}

        llm_client = RecordingLLMClient()
        runner = WorkflowRunner(
            config={},
            workflow_steps=self.make_steps(),
            prompt_loader=prompt_loader,
            context_builder=context_builder,
            llm_client=llm_client,
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(result.completed_step_ids, ["00-first", "01-second"])
        self.assertEqual(
            [call for call in calls if call[0] == "context"],
            [("context", "00-first"), ("context", "01-second")],
        )

    def test_runner_calls_prompt_loader_context_builder_llm_and_writes_output(self):
        prompt_calls = []
        context_calls = []
        llm_client = RecordingLLMClient("# Generated\n\nOutput")

        def prompt_loader(path, context):
            prompt_calls.append((path, context))
            return "# Rendered Prompt"

        def context_builder(step, input_path, output_root, completed_steps):
            context_calls.append(step.step_id)
            return {"APP_IDEA": "idea", "PROJECT_CONTEXT": ""}

        runner = WorkflowRunner(
            config={},
            workflow_steps=[self.make_steps()[0]],
            prompt_loader=prompt_loader,
            context_builder=context_builder,
            llm_client=llm_client,
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(len(prompt_calls), 1)
        self.assertEqual(context_calls, ["00-first"])
        self.assertEqual(llm_client.prompts, ["# Rendered Prompt"])
        self.assertTrue(result.output_paths["00-first"].exists())
        self.assertEqual(
            result.output_paths["00-first"].read_text(encoding="utf-8"),
            "# Generated\n\nOutput\n",
        )
        self.assertTrue((self.output_root / "README.md").is_file())
        self.assertTrue((self.output_root / "project-context.md").is_file())
        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.workflow_status, "completed")
        self.assertEqual(state.completed_steps, ["00-first"])
        self.assertIn("00-first", state.output_files)

    def test_failure_stops_workflow(self):
        llm_client = RecordingLLMClient("not markdown")
        runner = WorkflowRunner(
            config={"workflow": {"stop_on_failure": True}},
            workflow_steps=self.make_steps(),
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        with self.assertRaises(WorkflowRunError) as error:
            runner.run(self.input_path, self.output_root)

        self.assertIn("Step 00-first failed", str(error.exception))
        self.assertFalse((self.output_root / "01-second.md").exists())
        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.workflow_status, "failed")
        self.assertEqual(state.failed_step, "00-first")

    def test_dependencies_are_enforced(self):
        step = WorkflowStep(
            step_number=0,
            step_id="01-second",
            name="Second",
            prompt_template_path=Path("unused-second.md"),
            output_path=Path("01-second.md"),
            depends_on_step_ids=["00-first"],
        )
        runner = WorkflowRunner(
            config={},
            workflow_steps=[step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
        )

        with self.assertRaises(WorkflowRunError) as error:
            runner.run(self.input_path, self.output_root)

        self.assertIn("Missing completed dependencies", str(error.exception))

    def test_mock_full_run_creates_expected_files(self):
        runner = WorkflowRunner(
            config={"output": {"overwrite": False}},
            workflow_steps=WORKFLOW_STEPS,
            llm_client=FakeLLMClient(),
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(len(result.completed_step_ids), len(WORKFLOW_STEPS))
        for step in WORKFLOW_STEPS:
            with self.subTest(step_id=step.step_id):
                self.assertTrue((self.output_root / step.output_path).is_file())
        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(len(state.completed_steps), len(WORKFLOW_STEPS))
        self.assertIn("README", state.output_files)


if __name__ == "__main__":
    unittest.main()
