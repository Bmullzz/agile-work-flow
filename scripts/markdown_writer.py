"""Markdown output writer for generated workflow documents."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from scripts.file_utils import write_text_file


PathValue = Union[str, Path]


class MarkdownWriteError(ValueError):
    """Raised when Markdown output cannot be written safely."""


def write_markdown(
    output_root: PathValue,
    relative_path: PathValue,
    content: str,
    overwrite: bool = False,
) -> Path:
    if content is None or not content.strip():
        raise MarkdownWriteError("Markdown content cannot be empty.")

    root_path = _as_path(output_root, "output_root")
    output_path = _as_path(relative_path, "relative_path")

    if output_path.is_absolute():
        raise MarkdownWriteError("Markdown relative_path must not be absolute.")
    if output_path.suffix.lower() != ".md":
        raise MarkdownWriteError(
            f"Markdown output path must use a .md extension: {output_path}"
        )

    final_path = root_path / output_path
    normalized_content = _normalize_trailing_whitespace(content)
    return write_text_file(final_path, normalized_content, overwrite=overwrite)


def _normalize_trailing_whitespace(content: str) -> str:
    lines = [line.rstrip() for line in content.strip().splitlines()]
    return "\n".join(lines) + "\n"


def _as_path(path: PathValue, field_name: str) -> Path:
    if path is None:
        raise MarkdownWriteError(f"{field_name} cannot be None.")
    if isinstance(path, str) and path.strip() == "":
        raise MarkdownWriteError(f"{field_name} cannot be empty.")
    return Path(path)
