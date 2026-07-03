import tempfile
import unittest
from pathlib import Path

from scripts.file_utils import (
    copy_file,
    ensure_directory,
    file_exists,
    read_markdown_file,
    read_text_file,
    sanitize_slug,
    write_text_file,
)


class FileUtilsTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)

    def test_read_text_file(self):
        file_path = self.root / "note.txt"
        file_path.write_text("hello", encoding="utf-8")

        self.assertEqual(read_text_file(file_path), "hello")

    def test_read_missing_text_file_fails_clearly(self):
        with self.assertRaises(FileNotFoundError) as error:
            read_text_file(self.root / "missing.txt")

        self.assertIn("File not found", str(error.exception))

    def test_read_markdown_file_accepts_markdown_extensions(self):
        file_path = self.root / "idea.markdown"
        file_path.write_text("# Idea", encoding="utf-8")

        self.assertEqual(read_markdown_file(file_path), "# Idea")

    def test_read_markdown_file_rejects_non_markdown_extension(self):
        file_path = self.root / "idea.txt"
        file_path.write_text("# Idea", encoding="utf-8")

        with self.assertRaises(ValueError) as error:
            read_markdown_file(file_path)

        self.assertIn("Expected a Markdown file path", str(error.exception))

    def test_write_text_file(self):
        file_path = self.root / "output.txt"

        result = write_text_file(file_path, "generated")

        self.assertEqual(result, file_path)
        self.assertEqual(file_path.read_text(encoding="utf-8"), "generated")

    def test_write_text_file_creates_parent_folders(self):
        file_path = self.root / "nested" / "folder" / "output.txt"

        write_text_file(file_path, "generated")

        self.assertTrue(file_path.exists())
        self.assertEqual(file_path.read_text(encoding="utf-8"), "generated")

    def test_write_text_file_protects_existing_file_by_default(self):
        file_path = self.root / "output.txt"
        file_path.write_text("original", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            write_text_file(file_path, "new")

        self.assertEqual(file_path.read_text(encoding="utf-8"), "original")

    def test_write_text_file_overwrites_when_enabled(self):
        file_path = self.root / "output.txt"
        file_path.write_text("original", encoding="utf-8")

        write_text_file(file_path, "new", overwrite=True)

        self.assertEqual(file_path.read_text(encoding="utf-8"), "new")

    def test_ensure_directory_creates_nested_directory(self):
        directory_path = self.root / "one" / "two"

        result = ensure_directory(directory_path)

        self.assertEqual(result, directory_path)
        self.assertTrue(directory_path.is_dir())

    def test_copy_file_creates_parent_folder(self):
        source = self.root / "source.txt"
        destination = self.root / "copy" / "destination.txt"
        source.write_text("copy me", encoding="utf-8")

        result = copy_file(source, destination)

        self.assertEqual(result, destination)
        self.assertEqual(destination.read_text(encoding="utf-8"), "copy me")

    def test_copy_file_protects_existing_destination_by_default(self):
        source = self.root / "source.txt"
        destination = self.root / "destination.txt"
        source.write_text("source", encoding="utf-8")
        destination.write_text("destination", encoding="utf-8")

        with self.assertRaises(FileExistsError):
            copy_file(source, destination)

        self.assertEqual(destination.read_text(encoding="utf-8"), "destination")

    def test_copy_file_overwrites_when_enabled(self):
        source = self.root / "source.txt"
        destination = self.root / "destination.txt"
        source.write_text("source", encoding="utf-8")
        destination.write_text("destination", encoding="utf-8")

        copy_file(source, destination, overwrite=True)

        self.assertEqual(destination.read_text(encoding="utf-8"), "source")

    def test_file_exists_returns_boolean(self):
        file_path = self.root / "exists.txt"

        self.assertFalse(file_exists(file_path))
        file_path.write_text("exists", encoding="utf-8")
        self.assertTrue(file_exists(file_path))

    def test_sanitize_slug(self):
        self.assertEqual(sanitize_slug(" My Project: MVP! "), "my-project-mvp")
        self.assertEqual(sanitize_slug("Feature_001"), "feature-001")
        self.assertEqual(sanitize_slug(""), "untitled")

    def test_empty_path_fails_clearly(self):
        with self.assertRaises(ValueError) as error:
            write_text_file("", "content")

        self.assertIn("Path cannot be empty", str(error.exception))

    def test_cross_platform_path_inputs_are_supported(self):
        file_path = self.root / Path("nested") / Path("file.txt")

        write_text_file(str(file_path), "content")

        self.assertEqual(read_text_file(file_path), "content")


if __name__ == "__main__":
    unittest.main()
