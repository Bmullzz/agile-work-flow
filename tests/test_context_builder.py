import tempfile
import unittest
from pathlib import Path

from scripts.context_builder import ContextBuildError, build_context
from scripts.prompt_loader import render_prompt_file
from scripts.workflow_steps import WORKFLOW_STEPS, get_step_by_id


class ContextBuilderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.input_path = self.root / "input" / "app-idea.md"
        self.output_root = self.root / "output"
        self.input_path.parent.mkdir(parents=True)
        self.output_root.mkdir()
        self.input_path.write_text(
            "# App Idea\n\nBuild a local AI workflow planning tool.",
            encoding="utf-8",
        )

    def write_output(self, step_id: str, content: str) -> None:
        step = get_step_by_id(step_id)
        output_path = self.output_root / step.output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding="utf-8")

    def test_early_step_context_includes_app_idea(self):
        step = get_step_by_id("00-app-intake")

        context = build_context(step, self.input_path, self.output_root, [])

        self.assertIn("APP_IDEA", context)
        self.assertIn("Build a local AI workflow planning tool", context["APP_IDEA"])
        self.assertEqual(context["PROJECT_CONTEXT"], "")

    def test_later_step_context_includes_known_dependency_outputs(self):
        self.write_output("00-app-intake", "# Summary\n\nIntake content")
        step = get_step_by_id("01-product-vision")

        context = build_context(
            step,
            self.input_path,
            self.output_root,
            [get_step_by_id("00-app-intake")],
        )

        self.assertEqual(context["APP_INTAKE"], "# Summary\n\nIntake content")

    def test_missing_dependency_file_fails_clearly(self):
        step = get_step_by_id("01-product-vision")

        with self.assertRaises(ContextBuildError) as error:
            build_context(
                step,
                self.input_path,
                self.output_root,
                [get_step_by_id("00-app-intake")],
            )

        self.assertIn("Missing required dependency output", str(error.exception))
        self.assertIn("00-app-intake", str(error.exception))

    def test_context_excludes_unrelated_files(self):
        self.write_output("00-app-intake", "# Summary\n\nIntake content")
        unrelated_path = self.output_root / "99-unrelated.md"
        unrelated_path.write_text("Unrelated content", encoding="utf-8")
        step = get_step_by_id("01-product-vision")

        context = build_context(
            step,
            self.input_path,
            self.output_root,
            [get_step_by_id("00-app-intake")],
        )

        self.assertNotIn("Unrelated content", "\n".join(context.values()))

    def test_placeholder_names_are_stable(self):
        self.write_output("03-system-architecture", "# Architecture Overview\n\nCLI")
        self.write_output("07-technical-stories", "# Technical Story List\n\nStories")
        step = get_step_by_id("08-stories-by-application-layer")

        context = build_context(
            step,
            self.input_path,
            self.output_root,
            [
                get_step_by_id("03-system-architecture"),
                get_step_by_id("07-technical-stories"),
            ],
        )

        self.assertIn("SYSTEM_ARCHITECTURE", context)
        self.assertNotIn("TECH_STACK", context)

    def test_project_context_file_is_optional_but_loaded_when_present(self):
        project_context = self.input_path.parent / "project-context.md"
        project_context.write_text("# Project Context\n\nUse local files only.", encoding="utf-8")
        step = get_step_by_id("00-app-intake")

        context = build_context(step, self.input_path, self.output_root, [])

        self.assertIn("Use local files only.", context["PROJECT_CONTEXT"])

    def test_all_workflow_prompt_placeholders_can_be_rendered_from_context(self):
        completed_steps = []
        for step in WORKFLOW_STEPS:
            context = build_context(
                step,
                self.input_path,
                self.output_root,
                completed_steps,
            )
            rendered = render_prompt_file(step.prompt_template_path, context)

            self.assertNotIn("{{", rendered)
            self.write_output(step.step_id, f"# {step.name}\n\nGenerated output")
            completed_steps.append(step)


if __name__ == "__main__":
    unittest.main()
