import unittest
from pathlib import Path


PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

EXPECTED_PROMPT_FILES = [
    "00-app-intake.md",
    "01-product-vision.md",
    "02-tech-stack.md",
    "03-system-architecture.md",
    "04-user-journeys.md",
    "05-epics.md",
    "06-product-user-stories.md",
    "07-technical-stories.md",
    "08-stories-by-application-layer.md",
    "09-dependency-analysis.md",
    "10-phased-roadmap.md",
    "11-coding-agent-optimized-stories.md",
    "12-coding-agent-prompts.md",
    "13-project-setup-prompt.md",
    "14-qa-validation-plan.md",
    "15-documentation-plan.md",
]

REQUIRED_SECTIONS = [
    "## Role",
    "## Task",
    "## Input Context",
    "## Instructions",
    "## Required Output Format",
    "## Validation Checklist",
]


class PromptTemplateTests(unittest.TestCase):
    def test_every_expected_prompt_file_exists(self):
        for file_name in EXPECTED_PROMPT_FILES:
            with self.subTest(file_name=file_name):
                self.assertTrue((PROMPTS_DIR / file_name).is_file())

    def test_prompt_files_are_non_empty(self):
        for file_name in EXPECTED_PROMPT_FILES:
            with self.subTest(file_name=file_name):
                content = (PROMPTS_DIR / file_name).read_text(encoding="utf-8")
                self.assertTrue(content.strip())

    def test_prompt_files_include_required_sections(self):
        for file_name in EXPECTED_PROMPT_FILES:
            content = (PROMPTS_DIR / file_name).read_text(encoding="utf-8")
            with self.subTest(file_name=file_name):
                for section in REQUIRED_SECTIONS:
                    self.assertIn(section, content)


if __name__ == "__main__":
    unittest.main()
