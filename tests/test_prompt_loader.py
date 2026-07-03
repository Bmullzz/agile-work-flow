import tempfile
import unittest
from pathlib import Path

from scripts.prompt_loader import (
    PromptTemplateError,
    load_prompt_template,
    render_prompt,
    render_prompt_file,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]


class PromptLoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def write_template(self, name: str, content: str) -> Path:
        template_path = self.root / name
        template_path.write_text(content, encoding="utf-8")
        return template_path

    def test_load_existing_prompt(self):
        prompt_path = PROJECT_ROOT / "prompts" / "00-app-intake.md"

        template = load_prompt_template(prompt_path)

        self.assertIn("## Role", template)
        self.assertIn("{{APP_IDEA}}", template)

    def test_missing_prompt_fails(self):
        with self.assertRaises(FileNotFoundError) as error:
            load_prompt_template(self.root / "missing.md")

        self.assertIn("Prompt template not found", str(error.exception))

    def test_empty_prompt_fails(self):
        prompt_path = self.write_template("empty.md", "")

        with self.assertRaises(PromptTemplateError) as error:
            load_prompt_template(prompt_path)

        self.assertIn("Prompt template is empty", str(error.exception))

    def test_render_prompt_replaces_placeholders(self):
        rendered = render_prompt(
            "Task: {{APP_IDEA}}\nContext: {{PROJECT_CONTEXT}}",
            {
                "APP_IDEA": "Build a workflow tool",
                "PROJECT_CONTEXT": "Local Python CLI",
            },
        )

        self.assertIn("Build a workflow tool", rendered)
        self.assertIn("Local Python CLI", rendered)
        self.assertNotIn("{{APP_IDEA}}", rendered)

    def test_render_prompt_detects_unresolved_required_placeholders(self):
        with self.assertRaises(PromptTemplateError) as error:
            render_prompt("Task: {{APP_IDEA}}\nContext: {{PROJECT_CONTEXT}}", {})

        message = str(error.exception)
        self.assertIn("Missing required prompt context", message)
        self.assertIn("APP_IDEA", message)
        self.assertIn("PROJECT_CONTEXT", message)

    def test_render_prompt_file_loads_and_renders(self):
        prompt_path = self.write_template("prompt.md", "Build: {{APP_IDEA}}")

        rendered = render_prompt_file(prompt_path, {"APP_IDEA": "A local CLI"})

        self.assertEqual(rendered, "Build: A local CLI")


if __name__ == "__main__":
    unittest.main()
