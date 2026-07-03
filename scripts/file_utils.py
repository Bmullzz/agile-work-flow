"""Shared filesystem helpers for workflow modules."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Union


PathValue = Union[str, Path]


def read_text_file(path: PathValue) -> str:
    file_path = _as_path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    if not file_path.is_file():
        raise IsADirectoryError(f"Path is not a file: {file_path}")

    return file_path.read_text(encoding="utf-8")


def read_markdown_file(path: PathValue) -> str:
    file_path = _as_path(path)
    if file_path.suffix.lower() not in {".md", ".markdown"}:
        raise ValueError(f"Expected a Markdown file path, got: {file_path}")

    return read_text_file(file_path)


def write_text_file(path: PathValue, content: str, overwrite: bool = False) -> Path:
    file_path = _as_path(path)
    if file_path.exists() and not overwrite:
        raise FileExistsError(f"File already exists: {file_path}")

    ensure_directory(file_path.parent)
    file_path.write_text(content, encoding="utf-8")
    return file_path


def ensure_directory(path: PathValue) -> Path:
    directory_path = _as_path(path)
    if directory_path.exists() and not directory_path.is_dir():
        raise NotADirectoryError(f"Path exists and is not a directory: {directory_path}")

    directory_path.mkdir(parents=True, exist_ok=True)
    return directory_path


def copy_file(source: PathValue, destination: PathValue, overwrite: bool = False) -> Path:
    source_path = _as_path(source)
    destination_path = _as_path(destination)

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")
    if not source_path.is_file():
        raise IsADirectoryError(f"Source path is not a file: {source_path}")
    if destination_path.exists() and not overwrite:
        raise FileExistsError(f"Destination file already exists: {destination_path}")

    ensure_directory(destination_path.parent)
    shutil.copy2(source_path, destination_path)
    return destination_path


def file_exists(path: PathValue) -> bool:
    return _as_path(path).exists()


def sanitize_slug(value: str) -> str:
    if value is None:
        raise ValueError("Slug value cannot be None.")

    normalized = value.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "-", normalized)
    normalized = normalized.strip("-")
    return normalized or "untitled"


def _as_path(path: PathValue) -> Path:
    if path is None:
        raise ValueError("Path cannot be None.")
    if isinstance(path, str) and path.strip() == "":
        raise ValueError("Path cannot be empty.")

    file_path = Path(path).expanduser()
    if str(file_path).strip() == "":
        raise ValueError("Path cannot be empty.")

    return file_path
