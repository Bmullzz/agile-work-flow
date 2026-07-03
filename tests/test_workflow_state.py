import tempfile
import unittest
from pathlib import Path

from scripts.models import WorkflowStep
from scripts.workflow_state import (
    WorkflowStateError,
    create_initial_state,
    load_state,
    mark_downstream_steps_stale,
    mark_step_approved,
    mark_step_completed,
    mark_step_failed,
    mark_step_started,
    mark_step_skipped,
    mark_workflow_quit,
    save_state,
    state_file_path,
)


class WorkflowStateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.state_path = self.root / ".workflow-state.json"

    def test_create_state_file(self):
        state = create_initial_state(
            "test-project",
            "input/app-idea.md",
            "output/test-project",
            next_step="00-app-intake",
        )

        path = save_state(state, self.state_path)

        self.assertEqual(path, self.state_path)
        self.assertTrue(self.state_path.is_file())

    def test_save_state_writes_obsidian_visible_state_copy(self):
        state = create_initial_state(
            "test-project",
            "input/app-idea.md",
            "output/test-project",
        )

        save_state(state, self.state_path)

        meta_state_path = self.root / "99-meta" / "state" / "workflow-state.json"
        self.assertTrue(meta_state_path.is_file())
        self.assertEqual(
            load_state(self.state_path).to_dict(),
            load_state(meta_state_path).to_dict(),
        )

    def test_update_completed_steps(self):
        state = create_initial_state("test-project", "input.md", "output")

        mark_step_started(state, "00-app-intake", next_step="01-product-vision")
        mark_step_completed(
            state,
            "00-app-intake",
            "output/00-intake/00-app-intake.md",
            next_step="01-product-vision",
        )

        self.assertEqual(state.completed_steps, ["00-app-intake"])
        self.assertEqual(
            state.output_files["00-app-intake"],
            "output/00-intake/00-app-intake.md",
        )
        self.assertEqual(state.workflow_status, "running")
        self.assertEqual(state.next_step, "01-product-vision")

    def test_mark_failed_step(self):
        state = create_initial_state("test-project", "input.md", "output")

        mark_step_failed(state, "01-product-vision")

        self.assertEqual(state.workflow_status, "failed")
        self.assertEqual(state.failed_step, "01-product-vision")
        self.assertEqual(state.current_step, "01-product-vision")

    def test_mark_step_approved(self):
        state = create_initial_state("test-project", "input.md", "output")
        state.pending_review_step = "00-app-intake"

        mark_step_approved(state, "00-app-intake")

        self.assertEqual(state.approved_steps, ["00-app-intake"])
        self.assertIsNone(state.pending_review_step)

    def test_mark_step_skipped_tracks_output_without_completed_step(self):
        state = create_initial_state("test-project", "input.md", "output")

        mark_step_skipped(state, "00-app-intake", "output/00.md", next_step="01-next")

        self.assertEqual(state.completed_steps, [])
        self.assertEqual(state.output_files["00-app-intake"], "output/00.md")
        self.assertEqual(state.next_step, "01-next")

    def test_mark_workflow_quit_pauses_state(self):
        state = create_initial_state("test-project", "input.md", "output")

        mark_workflow_quit(state, "00-app-intake")

        self.assertEqual(state.workflow_status, "paused")
        self.assertEqual(state.current_step, "00-app-intake")
        self.assertEqual(state.next_step, "00-app-intake")
        self.assertEqual(state.pending_review_step, "00-app-intake")

    def test_mark_downstream_steps_stale_marks_direct_and_transitive_steps(self):
        steps = [
            WorkflowStep(0, "00-first", "First", "00.md", "00.md"),
            WorkflowStep(
                1,
                "01-second",
                "Second",
                "01.md",
                "01.md",
                depends_on_step_ids=["00-first"],
            ),
            WorkflowStep(
                2,
                "02-third",
                "Third",
                "02.md",
                "02.md",
                depends_on_step_ids=["01-second"],
            ),
        ]
        state = create_initial_state("test-project", "input.md", "output")
        state.approved_steps = ["00-first", "01-second", "02-third"]

        stale_step_ids = mark_downstream_steps_stale(state, "00-first", steps)

        self.assertEqual(stale_step_ids, ["01-second", "02-third"])
        self.assertEqual(state.stale_steps, ["01-second", "02-third"])
        self.assertEqual(state.approved_steps, ["00-first"])
        self.assertEqual(state.next_step, "01-second")

    def test_mark_downstream_steps_stale_keeps_stale_steps_in_workflow_order(self):
        steps = [
            WorkflowStep(0, "00-first", "First", "00.md", "00.md"),
            WorkflowStep(
                1,
                "01-second",
                "Second",
                "01.md",
                "01.md",
                depends_on_step_ids=["00-first"],
            ),
            WorkflowStep(
                2,
                "02-third",
                "Third",
                "02.md",
                "02.md",
                depends_on_step_ids=["01-second"],
            ),
        ]
        state = create_initial_state("test-project", "input.md", "output")
        state.stale_steps = ["02-third"]
        state.approved_steps = ["00-first", "01-second"]
        state.next_step = "02-third"

        stale_step_ids = mark_downstream_steps_stale(state, "00-first", steps)

        self.assertEqual(stale_step_ids, ["01-second"])
        self.assertEqual(state.stale_steps, ["01-second", "02-third"])
        self.assertEqual(state.next_step, "01-second")

    def test_mark_downstream_steps_stale_fails_for_unknown_step(self):
        state = create_initial_state("test-project", "input.md", "output")

        with self.assertRaises(KeyError):
            mark_downstream_steps_stale(state, "missing-step", [])

    def test_completed_step_clears_stale_state(self):
        state = create_initial_state("test-project", "input.md", "output")
        state.stale_steps = ["01-product-vision"]

        mark_step_completed(
            state,
            "01-product-vision",
            "output/01-product-vision.md",
            next_step=None,
        )

        self.assertEqual(state.stale_steps, [])

    def test_load_existing_state(self):
        state = create_initial_state("test-project", "input.md", "output")
        mark_step_completed(state, "00-app-intake", "output/00.md", next_step=None)
        save_state(state, self.state_path)

        loaded_state = load_state(self.state_path)

        self.assertEqual(loaded_state.project_name, "test-project")
        self.assertEqual(loaded_state.completed_steps, ["00-app-intake"])
        self.assertEqual(loaded_state.workflow_status, "completed")

    def test_handle_invalid_state(self):
        self.state_path.write_text("{invalid json", encoding="utf-8")

        with self.assertRaises(WorkflowStateError) as error:
            load_state(self.state_path)

        self.assertIn("Invalid workflow state JSON", str(error.exception))

    def test_state_file_path_uses_output_root(self):
        self.assertEqual(
            state_file_path(self.root / "output"),
            self.root / "output" / ".workflow-state.json",
        )


if __name__ == "__main__":
    unittest.main()
