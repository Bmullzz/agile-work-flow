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
                step_number=7,
                step_id="07-technical-stories",
                name="Technical Stories",
                prompt_template_path="prompts/07-technical-stories.md",
                output_path="04-stories/07-technical-stories.md",
            ),
            WorkflowStep(
                step_number=9,
                step_id="09-dependency-analysis",
                name="Dependency Analysis",
                prompt_template_path="prompts/09-dependency-analysis.md",
                output_path="05-planning/09-dependency-analysis.md",
            ),
            WorkflowStep(
                step_number=11,
                step_id="11-coding-agent-optimized-stories",
                name="Coding-Agent-Optimized Stories",
                prompt_template_path="prompts/11-coding-agent-optimized-stories.md",
                output_path="06-agent-prompts/11-coding-agent-optimized-stories.md",
            ),
            WorkflowStep(
                step_number=12,
                step_id="12-coding-agent-prompts",
                name="Coding-Agent Prompts",
                prompt_template_path="prompts/12-coding-agent-prompts.md",
                output_path="06-agent-prompts/12-coding-agent-prompts.md",
            ),
            WorkflowStep(
                step_number=13,
                step_id="13-project-setup-prompt",
                name="Project Setup Prompt",
                prompt_template_path="prompts/13-project-setup-prompt.md",
                output_path="06-agent-prompts/13-project-setup-prompt.md",
            ),
        ]
        self.write_output(self.steps[0], "# App Intake\n\nContent")
        self.write_output(self.steps[1], "# Technical Stories\n\nContent")
        self.write_output(self.steps[2], "# Dependency Analysis\n\nContent")
        self.write_output(self.steps[3], "# Optimized Stories\n\nContent")
        self.write_output(
            self.steps[4],
            "# Coding-Agent Prompts\n\n"
            "## TS-001 Phase 1 Setup Auth\n\n"
            "Implement auth scaffolding.\n\n"
            "## TS-002 Phase 1 Build CLI\n\n"
            "Implement CLI flow.",
        )
        self.write_output(self.steps[5], "# Project Setup Prompt\n\nCreate the project.")

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
        self.assertIn("(06-agent-prompts/prompt-index.md)", readme)
        self.assertIn("Coding-Agent Prompts", readme)

    def test_readme_uses_custom_codex_task_export_dir(self):
        IndexWriter().write_indexes(
            self.output_root,
            self.steps,
            run_metadata={"codex_task_export_dir": "custom/codex-tasks"},
        )

        readme = (self.output_root / "README.md").read_text(encoding="utf-8")

        self.assertIn("(custom/codex-tasks/)", readme)
        self.assertNotIn("(99-meta/codex-tasks/)", readme)

    def test_prompt_index_is_created(self):
        result = IndexWriter().write_indexes(self.output_root, self.steps)

        self.assertTrue(result.prompt_index_path.is_file())
        prompt_index = result.prompt_index_path.read_text(encoding="utf-8")
        self.assertIn("# Coding-Agent Prompt Index", prompt_index)
        self.assertIn("[Project Setup Prompt](13-project-setup-prompt.md)", prompt_index)
        self.assertIn("run this first", prompt_index)
        self.assertIn("../04-stories/07-technical-stories.md", prompt_index)
        self.assertIn("../05-planning/09-dependency-analysis.md", prompt_index)

    def test_agent_prompt_folder_structure_exists(self):
        IndexWriter().write_indexes(self.output_root, self.steps)

        self.assertTrue((self.output_root / "06-agent-prompts").is_dir())
        self.assertTrue((self.output_root / "06-agent-prompts" / "by-story").is_dir())
        self.assertTrue((self.output_root / "06-agent-prompts" / "by-phase").is_dir())

    def test_individual_prompt_files_are_created_from_combined_prompt(self):
        result = IndexWriter().write_indexes(self.output_root, self.steps)

        self.assertEqual(len(result.prompt_by_story_paths), 2)
        self.assertEqual(len(result.prompt_by_phase_paths), 1)
        first_prompt = self.output_root / "06-agent-prompts" / "by-story" / "ts-001.md"
        second_prompt = self.output_root / "06-agent-prompts" / "by-story" / "ts-002.md"
        phase_prompt = self.output_root / "06-agent-prompts" / "by-phase" / "phase-01.md"
        self.assertTrue(first_prompt.is_file())
        self.assertTrue(second_prompt.is_file())
        self.assertTrue(phase_prompt.is_file())
        self.assertIn("Implement auth scaffolding.", first_prompt.read_text(encoding="utf-8"))
        self.assertIn("../by-story/ts-001.md", phase_prompt.read_text(encoding="utf-8"))
        prompt_index = result.prompt_index_path.read_text(encoding="utf-8")
        self.assertLess(prompt_index.index("project-setup"), prompt_index.index("ts-001"))
        self.assertLess(prompt_index.index("ts-001"), prompt_index.index("ts-002"))

    def test_prompt_splitting_ignores_wrapper_sections(self):
        combined_prompt = self.output_root / "06-agent-prompts" / "12-coding-agent-prompts.md"
        combined_prompt.write_text(
            "# Coding-Agent Prompts\n\n"
            "## Prompt Index\n\n"
            "- TS-001: setup auth\n"
            "- TS-002: build cli\n\n"
            "## Coding Agent Prompts\n\n"
            "### TS-001 Phase 1 Setup Auth\n\n"
            "Implement auth scaffolding.\n\n"
            "### TS-002 Phase 1 Build CLI\n\n"
            "Implement CLI flow.\n\n"
            "## Shared Context\n\n"
            "Use the generated architecture.\n\n"
            "## Validation Notes\n\n"
            "Run the test suite.",
            encoding="utf-8",
        )

        result = IndexWriter().write_indexes(self.output_root, self.steps)

        prompt_names = sorted(path.name for path in result.prompt_by_story_paths)
        self.assertEqual(prompt_names, ["ts-001.md", "ts-002.md"])
        self.assertFalse(
            (self.output_root / "06-agent-prompts" / "by-story" / "001-prompt-index.md").exists()
        )
        first_prompt = (
            self.output_root / "06-agent-prompts" / "by-story" / "ts-001.md"
        ).read_text(encoding="utf-8")
        second_prompt = (
            self.output_root / "06-agent-prompts" / "by-story" / "ts-002.md"
        ).read_text(encoding="utf-8")
        self.assertIn("Implement auth scaffolding.", first_prompt)
        self.assertNotIn("Prompt Index", first_prompt)
        self.assertNotIn("Validation Notes", second_prompt)

    def test_missing_combined_prompt_warns_but_creates_prompt_index(self):
        combined_prompt = self.output_root / "06-agent-prompts" / "12-coding-agent-prompts.md"
        combined_prompt.unlink()

        result = IndexWriter().write_indexes(self.output_root, self.steps)

        self.assertTrue(result.prompt_index_path.is_file())
        self.assertEqual(result.prompt_by_story_paths, [])
        self.assertTrue(
            any("Missing combined coding-agent prompt file" in warning for warning in result.warnings)
        )
        prompt_index = result.prompt_index_path.read_text(encoding="utf-8")
        self.assertIn("Combined Coding-Agent Prompts", prompt_index)

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
