import tempfile
import unittest
from pathlib import Path

from scripts.validators import (
    validate_input_file,
    validate_markdown_content,
    validate_markdown_file,
)


class InputValidatorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def write_file(self, name: str, content: str) -> Path:
        file_path = self.root / name
        file_path.write_text(content, encoding="utf-8")
        return file_path

    def test_valid_minimal_input_passes(self):
        file_path = self.write_file(
            "app-idea.md",
            """
# App Idea

I want to build a local AI workflow tool that generates planning documents from an app idea.
""",
        )

        result = validate_input_file(file_path)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_full_structured_input_passes(self):
        file_path = self.write_file(
            "app-idea.md",
            """
# App Idea

Build a CLI that turns a product idea into agile planning documents for a solo developer.

## Users

Independent builders who want structured project plans.

## Outputs

- product brief
- backlog
- sprint plan
""",
        )

        result = validate_input_file(file_path)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_missing_file_fails(self):
        result = validate_input_file(self.root / "missing.md")

        self.assertFalse(result["is_valid"])
        self.assertIn("Input file was not found", result["errors"][0])

    def test_empty_file_fails(self):
        file_path = self.write_file("empty.md", "")

        result = validate_input_file(file_path)

        self.assertFalse(result["is_valid"])
        self.assertIn("Input file is empty", result["errors"][0])

    def test_non_markdown_file_fails(self):
        file_path = self.write_file(
            "app-idea.txt",
            "I want to build a local workflow tool for planning software projects.",
        )

        result = validate_input_file(file_path)

        self.assertFalse(result["is_valid"])
        self.assertIn("Markdown file", result["errors"][0])

    def test_too_vague_input_fails(self):
        for vague_value in ["App.", "Something with AI.", "I don't know."]:
            with self.subTest(vague_value=vague_value):
                file_path = self.write_file("app-idea.md", f"# App Idea\n\n{vague_value}")

                result = validate_input_file(file_path)

                self.assertFalse(result["is_valid"])
                self.assertTrue(
                    any("too vague" in error for error in result["errors"])
                )

    def test_missing_optional_fields_do_not_fail(self):
        file_path = self.write_file(
            "app-idea.md",
            """
# App Idea

Create a command line planning assistant that reads an app concept and writes useful project documents.
""",
        )

        result = validate_input_file(file_path)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_valid_markdown_content_passes_with_required_sections(self):
        result = validate_markdown_content(
            "# Product Vision\n\n## Overview\n\nBuild a local workflow planner.",
            required_sections=["Overview"],
        )

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_valid_markdown_content_allows_yaml_frontmatter(self):
        result = validate_markdown_content(
            "---\n"
            'title: "Product Vision"\n'
            'tags: ["ai-agile/product"]\n'
            "---\n\n"
            "# Product Vision\n\n## Overview\n\nBuild a local workflow planner.",
            required_sections=["Overview"],
        )

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])

    def test_empty_markdown_content_fails(self):
        result = validate_markdown_content("")

        self.assertFalse(result["is_valid"])
        self.assertIn("empty", result["errors"][0].lower())

    def test_markdown_without_heading_fails(self):
        result = validate_markdown_content("Build a local workflow planner.")

        self.assertFalse(result["is_valid"])
        self.assertIn("heading", result["errors"][0].lower())

    def test_missing_required_section_fails(self):
        result = validate_markdown_content(
            "# Product Vision\n\n## Overview\n\nBuild a local workflow planner.",
            required_sections=["Architecture"],
        )

        self.assertFalse(result["is_valid"])
        self.assertTrue(any("missing required sections" in error for error in result["errors"]))

    def test_validate_markdown_file_uses_required_sections(self):
        file_path = self.write_file(
            "doc.md",
            "# Product Vision\n\n## Overview\n\nBuild a local workflow planner.",
        )

        result = validate_markdown_file(file_path, required_sections=["Overview"])

        self.assertTrue(result["is_valid"])

    def test_open_questions_emit_warning(self):
        result = validate_markdown_content(
            "# Product Vision\n\n## Open Questions\n\n- What platform should we target?"
        )

        self.assertTrue(result["is_valid"])
        self.assertTrue(result["warnings"])

    def test_missing_app_idea_heading_warns_but_clear_description_passes(self):
        file_path = self.write_file(
            "idea.md",
            "Build a local command line workflow planner that creates agile documents from a product idea.",
        )

        result = validate_input_file(file_path)

        self.assertTrue(result["is_valid"])
        self.assertEqual(result["errors"], [])
        self.assertTrue(any("# App Idea" in warning for warning in result["warnings"]))


if __name__ == "__main__":
    unittest.main()
