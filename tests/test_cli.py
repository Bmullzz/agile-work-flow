import unittest
from contextlib import redirect_stderr
from io import StringIO
from pathlib import Path

from run_workflow import parse_args


class CliParsingTests(unittest.TestCase):
    def test_valid_required_arguments(self):
        args = parse_args(["--input", "input/app-idea.md", "--output", "output/my-project"])

        self.assertEqual(args.input, Path("input/app-idea.md"))
        self.assertEqual(args.output, Path("output/my-project"))

    def test_missing_input_exits_with_argparse_error(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as error:
                parse_args(["--output", "output/my-project"])

        self.assertNotEqual(error.exception.code, 0)

    def test_missing_output_exits_with_argparse_error(self):
        with redirect_stderr(StringIO()):
            with self.assertRaises(SystemExit) as error:
                parse_args(["--input", "input/app-idea.md"])

        self.assertNotEqual(error.exception.code, 0)

    def test_optional_flags_parse_correctly(self):
        args = parse_args(
            [
                "--input",
                "input/app-idea.md",
                "--output",
                "output/my-project",
                "--mock-llm",
                "--review",
                "--no-review",
                "--resume",
                "--overwrite",
            ]
        )

        self.assertTrue(args.mock_llm)
        self.assertTrue(args.review)
        self.assertTrue(args.no_review)
        self.assertTrue(args.resume)
        self.assertTrue(args.overwrite)

    def test_step_options_accept_string_values(self):
        args = parse_args(
            [
                "--input",
                "input/app-idea.md",
                "--output",
                "output/my-project",
                "--from-step",
                "backlog",
                "--step",
                "stories",
            ]
        )

        self.assertEqual(args.from_step, "backlog")
        self.assertEqual(args.step, "stories")


if __name__ == "__main__":
    unittest.main()
