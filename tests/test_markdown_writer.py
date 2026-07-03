import tempfile
import unittest
from pathlib import Path

from scripts.markdown_writer import MarkdownWriteError, write_markdown


class MarkdownWriterTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.output_root = Path(self.temp_dir.name) / "output"

    def test_write_markdown_file(self):
        result = write_markdown(
            self.output_root,
            "01-product-vision.md",
            "# Product Vision",
        )

        self.assertEqual(result, self.output_root / "01-product-vision.md")
        self.assertEqual(result.read_text(encoding="utf-8"), "# Product Vision\n")

    def test_write_markdown_creates_nested_folders(self):
        result = write_markdown(
            self.output_root,
            "01-product/01-product-vision.md",
            "# Product Vision",
        )

        self.assertTrue(result.exists())
        self.assertEqual(
            result,
            self.output_root / "01-product" / "01-product-vision.md",
        )

    def test_rejects_empty_content(self):
        with self.assertRaises(MarkdownWriteError) as error:
            write_markdown(self.output_root, "empty.md", "   ")

        self.assertIn("Markdown content cannot be empty", str(error.exception))

    def test_protects_existing_file_by_default(self):
        result = write_markdown(self.output_root, "existing.md", "# Original")

        with self.assertRaises(FileExistsError):
            write_markdown(self.output_root, "existing.md", "# New")

        self.assertEqual(result.read_text(encoding="utf-8"), "# Original\n")

    def test_allows_overwrite_when_configured(self):
        result = write_markdown(self.output_root, "existing.md", "# Original")

        write_markdown(self.output_root, "existing.md", "# New", overwrite=True)

        self.assertEqual(result.read_text(encoding="utf-8"), "# New\n")

    def test_rejects_invalid_relative_path(self):
        with self.assertRaises(MarkdownWriteError) as error:
            write_markdown(self.output_root, "", "# Content")

        self.assertIn("relative_path cannot be empty", str(error.exception))

    def test_rejects_absolute_relative_path(self):
        with self.assertRaises(MarkdownWriteError) as error:
            write_markdown(self.output_root, self.output_root / "absolute.md", "# Content")

        self.assertIn("relative_path must not be absolute", str(error.exception))

    def test_rejects_non_markdown_extension(self):
        with self.assertRaises(MarkdownWriteError) as error:
            write_markdown(self.output_root, "output.txt", "# Content")

        self.assertIn(".md extension", str(error.exception))

    def test_rejects_parent_directory_traversal(self):
        with self.assertRaises(MarkdownWriteError) as error:
            write_markdown(self.output_root, "../escape.md", "# Escape")

        self.assertIn("must stay inside output_root", str(error.exception))
        self.assertFalse((self.output_root.parent / "escape.md").exists())


if __name__ == "__main__":
    unittest.main()
