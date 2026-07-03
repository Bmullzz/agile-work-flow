import logging
import os
import tempfile
import unittest
from pathlib import Path

from scripts.logger import get_workflow_logger, redact_secrets, setup_workflow_logging


class LoggerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_log_file_is_created(self):
        logger, log_path = setup_workflow_logging(self.root, console=False)

        logger.info("workflow_start test=true")

        self.assertTrue(log_path.is_file())
        self.assertIn("workflow_start", log_path.read_text(encoding="utf-8"))

    def test_get_workflow_logger_returns_configured_logger(self):
        logger, _ = setup_workflow_logging(self.root, console=False)

        self.assertIs(get_workflow_logger(), logger)

    def test_secrets_are_redacted_from_log_file(self):
        original_key = os.environ.get("OPENAI_API_KEY")
        os.environ["OPENAI_API_KEY"] = "secret-test-key"
        self.addCleanup(self._restore_api_key, original_key)
        logger, log_path = setup_workflow_logging(self.root, console=False)

        logger.error("provider failed with secret-test-key and sk-testsecret123")

        content = log_path.read_text(encoding="utf-8")
        self.assertNotIn("secret-test-key", content)
        self.assertNotIn("sk-testsecret123", content)
        self.assertIn("[redacted]", content)

    def test_redact_secrets_handles_api_key_assignments(self):
        redacted = redact_secrets("api_key=abc123 token:xyz789")

        self.assertNotIn("abc123", redacted)
        self.assertNotIn("xyz789", redacted)

    def tearDown(self):
        logger = logging.getLogger("ai_agile_workflow")
        for handler in list(logger.handlers):
            logger.removeHandler(handler)
            handler.close()

    def _restore_api_key(self, value):
        os.environ.pop("OPENAI_API_KEY", None)
        if value is not None:
            os.environ["OPENAI_API_KEY"] = value


if __name__ == "__main__":
    unittest.main()
