import tempfile
import unittest
from pathlib import Path

from scripts.config_loader import ConfigError, load_config


class ConfigLoaderTests(unittest.TestCase):
    def write_config(self, content: str) -> Path:
        temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(temp_dir.cleanup)
        config_path = Path(temp_dir.name) / "config.yaml"
        config_path.write_text(content, encoding="utf-8")
        return config_path

    def test_valid_config_loads(self):
        config_path = self.write_config(
            """
llm:
  provider: openai
  model: test-model
workflow:
  default_review: false
output:
  format: markdown
prompts:
  directory: prompts
"""
        )

        config = load_config(config_path)

        self.assertEqual(config["llm"]["provider"], "openai")
        self.assertEqual(config["llm"]["model"], "test-model")
        self.assertFalse(config["workflow"]["default_review"])
        self.assertEqual(config["output"]["format"], "markdown")
        self.assertEqual(config["prompts"]["directory"], "prompts")

    def test_missing_config_fails(self):
        with self.assertRaises(FileNotFoundError) as error:
            load_config("missing-config.yaml")

        self.assertIn("Config file not found", str(error.exception))

    def test_invalid_yaml_fails(self):
        config_path = self.write_config(
            """
llm:
  provider: openai
workflow: [
"""
        )

        with self.assertRaises(ConfigError) as error:
            load_config(config_path)

        self.assertIn("Invalid YAML", str(error.exception))

    def test_missing_required_section_fails(self):
        config_path = self.write_config(
            """
llm: {}
workflow: {}
output: {}
"""
        )

        with self.assertRaises(ConfigError) as error:
            load_config(config_path)

        self.assertIn("Missing required config section: prompts", str(error.exception))

    def test_defaults_are_applied(self):
        config_path = self.write_config(
            """
llm: {}
workflow: {}
output: {}
prompts: {}
"""
        )

        config = load_config(config_path)

        self.assertEqual(config["llm"]["temperature"], 0.2)
        self.assertEqual(config["llm"]["max_retries"], 2)
        self.assertTrue(config["workflow"]["resume_enabled"])
        self.assertFalse(config["output"]["overwrite"])
        self.assertEqual(config["prompts"]["extension"], ".md")

    def test_secrets_are_not_allowed_in_yaml(self):
        config_path = self.write_config(
            """
llm:
  api_key: not-here
workflow: {}
output: {}
prompts: {}
"""
        )

        with self.assertRaises(ConfigError) as error:
            load_config(config_path)

        self.assertIn("must not be stored in config.yaml", str(error.exception))


if __name__ == "__main__":
    unittest.main()
