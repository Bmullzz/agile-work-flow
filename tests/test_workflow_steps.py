import unittest
from pathlib import Path

from scripts.workflow_steps import (
    WORKFLOW_STEPS,
    get_single_step,
    get_step_by_id,
    get_steps_from,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

EXPECTED_STEP_IDS = [
    "00-app-intake",
    "01-product-vision",
    "02-tech-stack",
    "03-system-architecture",
    "04-user-journeys",
    "05-epics",
    "06-product-user-stories",
    "07-technical-stories",
    "08-stories-by-application-layer",
    "09-dependency-analysis",
    "10-phased-roadmap",
    "11-coding-agent-optimized-stories",
    "12-coding-agent-prompts",
    "13-project-setup-prompt",
    "14-qa-validation-plan",
    "15-documentation-plan",
]


class WorkflowStepRegistryTests(unittest.TestCase):
    def test_every_expected_step_exists_in_order(self):
        self.assertEqual([step.step_id for step in WORKFLOW_STEPS], EXPECTED_STEP_IDS)

    def test_step_ids_are_unique(self):
        step_ids = [step.step_id for step in WORKFLOW_STEPS]

        self.assertEqual(len(step_ids), len(set(step_ids)))

    def test_step_numbers_are_sequential(self):
        self.assertEqual(
            [step.step_number for step in WORKFLOW_STEPS],
            list(range(len(WORKFLOW_STEPS))),
        )

    def test_prompt_files_exist(self):
        for step in WORKFLOW_STEPS:
            with self.subTest(step_id=step.step_id):
                self.assertTrue((PROJECT_ROOT / step.prompt_template_path).is_file())

    def test_output_paths_are_unique(self):
        output_paths = [step.output_path for step in WORKFLOW_STEPS]

        self.assertEqual(len(output_paths), len(set(output_paths)))

    def test_dependencies_point_to_earlier_valid_steps(self):
        step_number_by_id = {step.step_id: step.step_number for step in WORKFLOW_STEPS}

        for step in WORKFLOW_STEPS:
            with self.subTest(step_id=step.step_id):
                for dependency_id in step.depends_on_step_ids:
                    self.assertIn(dependency_id, step_number_by_id)
                    self.assertLess(
                        step_number_by_id[dependency_id], step.step_number
                    )

    def test_required_sections_are_defined_for_every_step(self):
        for step in WORKFLOW_STEPS:
            with self.subTest(step_id=step.step_id):
                self.assertTrue(step.required_sections)

    def test_get_step_by_id_returns_matching_step(self):
        step = get_step_by_id("03-system-architecture")

        self.assertEqual(step.step_id, "03-system-architecture")
        self.assertEqual(step.name, "System Architecture")

    def test_get_step_by_id_fails_for_unknown_step(self):
        with self.assertRaises(KeyError):
            get_step_by_id("unknown-step")

    def test_get_steps_from_returns_requested_step_and_following_steps(self):
        steps = get_steps_from("13-project-setup-prompt")

        self.assertEqual(
            [step.step_id for step in steps],
            [
                "13-project-setup-prompt",
                "14-qa-validation-plan",
                "15-documentation-plan",
            ],
        )

    def test_get_single_step_returns_one_step_list(self):
        steps = get_single_step("10-phased-roadmap")

        self.assertEqual(len(steps), 1)
        self.assertEqual(steps[0].step_id, "10-phased-roadmap")


if __name__ == "__main__":
    unittest.main()
