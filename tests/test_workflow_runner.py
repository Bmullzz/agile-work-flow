import tempfile
import unittest
from pathlib import Path

from scripts.llm_client import FakeLLMClient
from scripts.models import WorkflowStep
from scripts.review_gate import ReviewDecision
from scripts.workflow_runner import WorkflowRunError, WorkflowRunner
from scripts.workflow_state import (
    create_initial_state,
    load_state,
    mark_step_completed,
    save_state,
)
from scripts.workflow_steps import WORKFLOW_STEPS


class RecordingLLMClient:
    def __init__(self, response: str = "# Generated\n\nContent"):
        self.prompts = []
        self.response = response

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        return self.response


class SequencedLLMClient:
    def __init__(self):
        self.prompts = []
        self.count = 0

    def generate(self, prompt: str) -> str:
        self.prompts.append(prompt)
        self.count += 1
        return f"# Generated {self.count}\n\nContent"


class ScriptedReviewGate:
    def __init__(self, decisions):
        self.decisions = list(decisions)
        self.calls = []

    def review(self, step, output_path):
        self.calls.append((step.step_id, output_path))
        if not self.decisions:
            raise AssertionError("No scripted review decisions remaining")
        return self.decisions.pop(0)


class FailingReviewGate:
    def review(self, step, output_path):
        raise AssertionError("Review gate should not be called")


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

    def make_three_steps(self):
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
            WorkflowStep(
                step_number=2,
                step_id="02-third",
                name="Third",
                prompt_template_path=Path("unused-third.md"),
                output_path=Path("02-third.md"),
                depends_on_step_ids=["01-second"],
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
        self.assertIn(
            'document_id: "00-first"',
            result.output_paths["00-first"].read_text(encoding="utf-8"),
        )
        self.assertEqual(
            self._markdown_body(result.output_paths["00-first"]),
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

    def test_missing_required_section_stops_workflow(self):
        llm_client = RecordingLLMClient("# Generated\n\nNo required section here")
        step = WorkflowStep(
            step_number=0,
            step_id="00-first",
            name="First",
            prompt_template_path=Path("unused-first.md"),
            output_path=Path("00-first.md"),
            required_sections=["Overview"],
        )
        runner = WorkflowRunner(
            config={"workflow": {"stop_on_failure": True}},
            workflow_steps=[step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        with self.assertRaises(WorkflowRunError) as error:
            runner.run(self.input_path, self.output_root)

        self.assertIn("missing required sections", str(error.exception).lower())
        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.workflow_status, "failed")

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

    def test_resume_after_partial_state(self):
        first_step, second_step = self.make_steps()
        first_output = self.output_root / first_step.output_path
        first_output.parent.mkdir(parents=True, exist_ok=True)
        first_output.write_text("# Existing First\n\nContent", encoding="utf-8")
        state = create_initial_state(
            "output",
            self.input_path,
            self.output_root,
            next_step=second_step.step_id,
        )
        mark_step_completed(
            state,
            first_step.step_id,
            first_output,
            next_step=second_step.step_id,
        )
        save_state(state, self.output_root / ".workflow-state.json")
        llm_client = RecordingLLMClient("# Generated Second\n\nContent")
        runner = WorkflowRunner(
            config={},
            workflow_steps=self.make_steps(),
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        result = runner.run(self.input_path, self.output_root, resume=True)

        self.assertEqual(result.completed_step_ids, [second_step.step_id])
        self.assertEqual(len(llm_client.prompts), 1)
        self.assertTrue((self.output_root / second_step.output_path).is_file())

    def test_skip_existing_valid_outputs_by_default(self):
        first_step = self.make_steps()[0]
        existing_output = self.output_root / first_step.output_path
        existing_output.parent.mkdir(parents=True, exist_ok=True)
        existing_output.write_text("# Existing\n\nContent", encoding="utf-8")
        llm_client = RecordingLLMClient("# New\n\nContent")
        runner = WorkflowRunner(
            config={"output": {"overwrite": False}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(result.skipped_step_ids, [first_step.step_id])
        self.assertEqual(llm_client.prompts, [])
        self.assertEqual(existing_output.read_text(encoding="utf-8"), "# Existing\n\nContent")

    def test_strict_warning_mode_skips_existing_clean_output(self):
        first_step = self.make_steps()[0]
        existing_output = self.output_root / first_step.output_path
        existing_output.parent.mkdir(parents=True, exist_ok=True)
        existing_output.write_text("# Existing\n\nContent", encoding="utf-8")
        llm_client = RecordingLLMClient("# New\n\nContent")
        runner = WorkflowRunner(
            config={
                "workflow": {"fail_on_warnings": True},
                "output": {"overwrite": False},
            },
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(result.skipped_step_ids, [first_step.step_id])
        self.assertEqual(llm_client.prompts, [])
        self.assertEqual(existing_output.read_text(encoding="utf-8"), "# Existing\n\nContent")

    def test_overwrite_regenerates_existing_outputs(self):
        first_step = self.make_steps()[0]
        existing_output = self.output_root / first_step.output_path
        existing_output.parent.mkdir(parents=True, exist_ok=True)
        existing_output.write_text("# Existing\n\nContent", encoding="utf-8")
        llm_client = RecordingLLMClient("# New\n\nContent")
        runner = WorkflowRunner(
            config={"output": {"overwrite": True}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(result.skipped_step_ids, [])
        self.assertEqual(len(llm_client.prompts), 1)
        self.assertEqual(self._markdown_body(existing_output), "# New\n\nContent\n")

    def test_step_mode_runs_only_selected_step_and_requires_dependencies(self):
        first_step, second_step = self.make_steps()
        first_output = self.output_root / first_step.output_path
        first_output.parent.mkdir(parents=True, exist_ok=True)
        first_output.write_text("# Existing First\n\nContent", encoding="utf-8")
        llm_client = RecordingLLMClient("# Generated Second\n\nContent")
        runner = WorkflowRunner(
            config={},
            workflow_steps=self.make_steps(),
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        result = runner.run(
            self.input_path,
            self.output_root,
            step_id=second_step.step_id,
        )

        self.assertEqual(result.completed_step_ids, [second_step.step_id])
        self.assertEqual(len(llm_client.prompts), 1)
        self.assertTrue((self.output_root / second_step.output_path).is_file())

    def test_step_mode_missing_dependencies_fails(self):
        second_step = self.make_steps()[1]
        runner = WorkflowRunner(
            config={},
            workflow_steps=self.make_steps(),
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
        )

        with self.assertRaises(WorkflowRunError) as error:
            runner.run(self.input_path, self.output_root, step_id=second_step.step_id)

        self.assertIn("Missing completed dependencies", str(error.exception))

    def test_from_step_runs_selected_and_downstream_steps(self):
        first_step = self.make_steps()[0]
        first_output = self.output_root / first_step.output_path
        first_output.parent.mkdir(parents=True, exist_ok=True)
        first_output.write_text("# Existing First\n\nContent", encoding="utf-8")
        llm_client = SequencedLLMClient()
        runner = WorkflowRunner(
            config={"output": {"overwrite": True}},
            workflow_steps=self.make_steps(),
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
        )

        result = runner.run(
            self.input_path,
            self.output_root,
            from_step_id=first_step.step_id,
        )

        self.assertEqual(result.completed_step_ids, ["00-first", "01-second"])
        self.assertEqual(len(llm_client.prompts), 2)

    def test_invalid_step_id_fails(self):
        runner = WorkflowRunner(
            config={},
            workflow_steps=self.make_steps(),
            llm_client=RecordingLLMClient(),
        )

        with self.assertRaises(WorkflowRunError) as error:
            runner.run(self.input_path, self.output_root, step_id="missing-step")

        self.assertIn("Unknown workflow step ID", str(error.exception))

    def test_full_auto_mode_bypasses_review_gate(self):
        first_step = self.make_steps()[0]
        runner = WorkflowRunner(
            config={"workflow": {"default_review": False}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
            review_gate=FailingReviewGate(),
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(result.completed_step_ids, [first_step.step_id])

    def test_review_approve_marks_step_approved(self):
        first_step = self.make_steps()[0]
        review_gate = ScriptedReviewGate([ReviewDecision.APPROVE])
        runner = WorkflowRunner(
            config={"workflow": {"default_review": True}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
            review_gate=review_gate,
        )

        runner.run(self.input_path, self.output_root)

        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.approved_steps, [first_step.step_id])
        self.assertEqual(len(review_gate.calls), 1)

    def test_review_regenerate_reruns_current_step(self):
        first_step = self.make_steps()[0]
        review_gate = ScriptedReviewGate(
            [ReviewDecision.REGENERATE, ReviewDecision.APPROVE]
        )
        llm_client = SequencedLLMClient()
        runner = WorkflowRunner(
            config={"workflow": {"default_review": True}, "output": {"overwrite": True}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=llm_client,
            review_gate=review_gate,
        )

        result = runner.run(self.input_path, self.output_root)

        self.assertEqual(len(llm_client.prompts), 2)
        self.assertEqual(
            self._markdown_body(result.output_paths[first_step.step_id]),
            "# Generated 2\n\nContent\n",
        )

    def test_review_quit_saves_paused_state(self):
        first_step = self.make_steps()[0]
        review_gate = ScriptedReviewGate([ReviewDecision.QUIT])
        runner = WorkflowRunner(
            config={"workflow": {"default_review": True}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
            review_gate=review_gate,
        )

        result = runner.run(self.input_path, self.output_root)

        state = load_state(self.output_root / ".workflow-state.json")
        self.assertTrue(result.quit_requested)
        self.assertEqual(state.workflow_status, "paused")
        self.assertEqual(state.pending_review_step, first_step.step_id)
        self.assertFalse((self.output_root / "README.md").exists())

    def test_review_mode_blocks_downstream_until_dependency_approved(self):
        first_step, second_step = self.make_steps()
        first_output = self.output_root / first_step.output_path
        first_output.parent.mkdir(parents=True, exist_ok=True)
        first_output.write_text("# Existing First\n\nContent", encoding="utf-8")
        state = create_initial_state(
            "output",
            self.input_path,
            self.output_root,
            next_step=second_step.step_id,
        )
        mark_step_completed(
            state,
            first_step.step_id,
            first_output,
            next_step=second_step.step_id,
        )
        save_state(state, self.output_root / ".workflow-state.json")
        runner = WorkflowRunner(
            config={"workflow": {"default_review": True}},
            workflow_steps=self.make_steps(),
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
            review_gate=ScriptedReviewGate([ReviewDecision.APPROVE]),
        )

        with self.assertRaises(WorkflowRunError) as error:
            runner.run(self.input_path, self.output_root, step_id=second_step.step_id)

        self.assertIn("Unapproved dependencies", str(error.exception))

    def test_review_skip_marks_step_approved_for_downstream_use(self):
        first_step = self.make_steps()[0]
        existing_output = self.output_root / first_step.output_path
        existing_output.parent.mkdir(parents=True, exist_ok=True)
        existing_output.write_text("# Existing\n\nContent", encoding="utf-8")
        review_gate = ScriptedReviewGate([ReviewDecision.SKIP])
        runner = WorkflowRunner(
            config={"workflow": {"default_review": True}, "output": {"overwrite": True}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
            review_gate=review_gate,
        )

        runner.run(self.input_path, self.output_root)

        state = load_state(self.output_root / ".workflow-state.json")
        self.assertIn(first_step.step_id, state.approved_steps)

    def test_review_edit_marks_downstream_steps_stale(self):
        steps = self.make_three_steps()
        self._write_completed_approved_state(steps)
        review_gate = ScriptedReviewGate([ReviewDecision.EDIT])
        runner = WorkflowRunner(
            config={"workflow": {"default_review": True}, "output": {"overwrite": True}},
            workflow_steps=steps,
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
            review_gate=review_gate,
        )

        runner.run(self.input_path, self.output_root, step_id="00-first")

        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.stale_steps, ["01-second", "02-third"])
        self.assertEqual(state.approved_steps, ["00-first"])
        self.assertEqual(state.workflow_status, "stale")
        self.assertEqual(state.next_step, "01-second")

    def test_review_regenerate_marks_downstream_steps_stale(self):
        steps = self.make_three_steps()
        self._write_completed_approved_state(steps)
        review_gate = ScriptedReviewGate(
            [ReviewDecision.REGENERATE, ReviewDecision.APPROVE]
        )
        runner = WorkflowRunner(
            config={"workflow": {"default_review": True}, "output": {"overwrite": True}},
            workflow_steps=steps,
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=SequencedLLMClient(),
            review_gate=review_gate,
        )

        runner.run(self.input_path, self.output_root, step_id="00-first")

        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.stale_steps, ["01-second", "02-third"])
        self.assertNotIn("01-second", state.approved_steps)
        self.assertNotIn("02-third", state.approved_steps)

    def test_stale_dependencies_are_not_used_as_context(self):
        first_step, second_step = self.make_steps()
        first_output = self.output_root / first_step.output_path
        first_output.parent.mkdir(parents=True, exist_ok=True)
        first_output.write_text("# Existing First\n\nContent", encoding="utf-8")
        state = create_initial_state(
            "output",
            self.input_path,
            self.output_root,
            next_step=second_step.step_id,
        )
        mark_step_completed(
            state,
            first_step.step_id,
            first_output,
            next_step=second_step.step_id,
        )
        state.stale_steps = [first_step.step_id]
        save_state(state, self.output_root / ".workflow-state.json")
        runner = WorkflowRunner(
            config={},
            workflow_steps=self.make_steps(),
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient(),
        )

        with self.assertRaises(WorkflowRunError) as error:
            runner.run(self.input_path, self.output_root, step_id=second_step.step_id)

        self.assertIn("Stale dependencies", str(error.exception))

    def test_rerun_clears_stale_state_for_regenerated_step(self):
        steps = self.make_steps()
        first_step = steps[0]
        first_output = self.output_root / first_step.output_path
        first_output.parent.mkdir(parents=True, exist_ok=True)
        first_output.write_text("# Stale First\n\nContent", encoding="utf-8")
        state = create_initial_state(
            "output",
            self.input_path,
            self.output_root,
            next_step=first_step.step_id,
        )
        mark_step_completed(
            state,
            first_step.step_id,
            first_output,
            next_step=first_step.step_id,
        )
        state.stale_steps = [first_step.step_id]
        save_state(state, self.output_root / ".workflow-state.json")
        runner = WorkflowRunner(
            config={"output": {"overwrite": False}},
            workflow_steps=[first_step],
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient("# Regenerated\n\nContent"),
        )

        runner.run(self.input_path, self.output_root, step_id=first_step.step_id)

        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.stale_steps, [])
        self.assertEqual(
            self._markdown_body(first_output),
            "# Regenerated\n\nContent\n",
        )

    def test_resume_starts_from_first_stale_step(self):
        steps = self.make_three_steps()
        self._write_completed_approved_state(steps)
        state = load_state(self.output_root / ".workflow-state.json")
        state.stale_steps = ["01-second", "02-third"]
        state.approved_steps = ["00-first"]
        state.next_step = None
        save_state(state, self.output_root / ".workflow-state.json")
        runner = WorkflowRunner(
            config={"output": {"overwrite": False}},
            workflow_steps=steps,
            prompt_loader=lambda path, context: "# Prompt",
            context_builder=lambda step, input_path, output_root, completed_steps: {},
            llm_client=RecordingLLMClient("# Regenerated\n\nContent"),
        )

        result = runner.run(self.input_path, self.output_root, resume=True)

        self.assertEqual(result.completed_step_ids, ["01-second", "02-third"])
        state = load_state(self.output_root / ".workflow-state.json")
        self.assertEqual(state.stale_steps, [])
        self.assertEqual(state.workflow_status, "completed")

    def _write_completed_approved_state(self, steps):
        state = create_initial_state(
            "output",
            self.input_path,
            self.output_root,
            next_step=None,
        )
        for index, step in enumerate(steps):
            output_path = self.output_root / step.output_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(f"# Existing {step.name}\n\nContent", encoding="utf-8")
            next_step = steps[index + 1].step_id if index + 1 < len(steps) else None
            mark_step_completed(state, step.step_id, output_path, next_step=next_step)
            state.approved_steps.append(step.step_id)
        save_state(state, self.output_root / ".workflow-state.json")
        return state

    def _markdown_body(self, path: Path) -> str:
        content = path.read_text(encoding="utf-8")
        if content.startswith("---\n"):
            _, _, content = content.partition("\n---\n")
            return content.lstrip()
        return content


if __name__ == "__main__":
    unittest.main()
