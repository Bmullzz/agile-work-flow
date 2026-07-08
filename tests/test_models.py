import unittest
from pathlib import Path

from scripts.models import WorkflowState, WorkflowStep


class WorkflowStepTests(unittest.TestCase):
    def test_construct_minimal_valid_step(self):
        step = WorkflowStep(
            step_number=0,
            step_id="app-intake",
            name="App Intake",
            prompt_template_path="prompts/00-app-intake.md",
            output_path="output/app-intake.md",
        )

        self.assertEqual(step.step_number, 0)
        self.assertEqual(step.step_id, "app-intake")
        self.assertEqual(step.name, "App Intake")
        self.assertEqual(step.prompt_template_path, Path("prompts/00-app-intake.md"))
        self.assertEqual(step.output_path, Path("output/app-intake.md"))
        self.assertEqual(step.depends_on_step_ids, [])
        self.assertEqual(step.required_sections, [])
        self.assertEqual(step.blocks_step_ids, [])
        self.assertEqual(step.status, "pending")
        self.assertEqual(step.review_status, "not_required")
        self.assertFalse(step.can_skip)
        self.assertFalse(step.stale)

    def test_construct_step_with_dependencies(self):
        step = WorkflowStep(
            step_number=2,
            step_id="tech-stack",
            name="Tech Stack",
            prompt_template_path=Path("prompts/02-tech-stack.md"),
            output_path=Path("output/02-tech-stack.md"),
            depends_on_step_ids=["app-intake", "product-vision"],
            required_sections=["Recommended Stack", "Testing Approach"],
            blocks_step_ids=["system-architecture"],
            status="ready",
            review_status="approved",
            can_skip=True,
            stale=True,
        )

        self.assertEqual(step.depends_on_step_ids, ["app-intake", "product-vision"])
        self.assertEqual(
            step.required_sections, ["Recommended Stack", "Testing Approach"]
        )
        self.assertEqual(step.blocks_step_ids, ["system-architecture"])
        self.assertEqual(step.status, "ready")
        self.assertEqual(step.review_status, "approved")
        self.assertTrue(step.can_skip)
        self.assertTrue(step.stale)

    def test_list_defaults_do_not_share_mutable_state(self):
        first = WorkflowStep(
            step_number=0,
            step_id="first",
            name="First",
            prompt_template_path="prompts/first.md",
            output_path="output/first.md",
        )
        second = WorkflowStep(
            step_number=1,
            step_id="second",
            name="Second",
            prompt_template_path="prompts/second.md",
            output_path="output/second.md",
        )

        first.depends_on_step_ids.append("dependency")
        first.required_sections.append("Section")
        first.blocks_step_ids.append("blocked")

        self.assertEqual(second.depends_on_step_ids, [])
        self.assertEqual(second.required_sections, [])
        self.assertEqual(second.blocks_step_ids, [])

    def test_required_fields_are_validated(self):
        with self.assertRaises(TypeError):
            WorkflowStep()

        with self.assertRaises(ValueError):
            WorkflowStep(
                step_number=0,
                step_id="",
                name="Missing ID",
                prompt_template_path="prompts/missing-id.md",
                output_path="output/missing-id.md",
            )

        with self.assertRaises(ValueError):
            WorkflowStep(
                step_number=0,
                step_id="missing-path",
                name="Missing Path",
                prompt_template_path="",
                output_path="output/missing-path.md",
            )


class WorkflowStateModelTests(unittest.TestCase):
    def test_generated_documents_default_and_serialization(self):
        state = WorkflowState(
            project_name="test-project",
            input_file="input/app-idea.md",
            output_folder="output/test-project",
        )

        self.assertEqual(state.generated_documents, {})

        state.generated_documents["00-app-intake"] = {
            "step_id": "00-app-intake",
            "generation_backend": "mock",
            "generation_mode": "deterministic_mock",
        }

        loaded = WorkflowState.from_dict(state.to_dict())

        self.assertEqual(
            loaded.generated_documents["00-app-intake"]["generation_backend"],
            "mock",
        )


if __name__ == "__main__":
    unittest.main()
