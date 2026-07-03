"""Input and Markdown validation helpers for workflow startup."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Union

from scripts.logger import get_workflow_logger


PathValue = Union[str, Path]

VAGUE_INPUTS = {
    "app",
    "app.",
    "something with ai",
    "something with ai.",
    "i don't know",
    "i don't know.",
    "i dont know",
    "i dont know.",
}


def validate_input_file(path: PathValue) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    try:
        file_path = _as_path(path)
    except ValueError as error:
        return _result(path=path, is_valid=False, errors=[str(error)], warnings=warnings)

    if file_path.suffix.lower() != ".md":
        errors.append(
            "Input file must be a Markdown file with a .md extension. "
            f"Got: {file_path}"
        )

    if not file_path.exists():
        errors.append(
            "Input file was not found. Provide a path to an app idea Markdown file."
        )
        return _result(file_path, False, errors, warnings)

    if not file_path.is_file():
        errors.append(f"Input path must point to a file, not a directory: {file_path}")
        return _result(file_path, False, errors, warnings)

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as error:
        errors.append(f"Input file could not be read: {error}")
        return _result(file_path, False, errors, warnings)

    if not content.strip():
        errors.append(
            "Input file is empty. Add a short Markdown description under '# App Idea'."
        )
        return _result(file_path, False, errors, warnings)

    if not _has_app_idea_heading(content):
        warnings.append(
            "Input file does not include '# App Idea'. This heading is recommended "
            "but not required when the description is clear."
        )

    meaningful_text = _extract_meaningful_text(content)
    if not _is_meaningful_app_idea(meaningful_text):
        errors.append(
            "Input file is too vague. Add one or two sentences describing the app, "
            "its users, and what it should do."
        )

    return _result(file_path, not errors, errors, warnings)


def validate_markdown_content(
    content: str,
    required_sections: list[str] | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []

    if content is None or not content.strip():
        errors.append("Generated Markdown is empty.")
        return _result(path=None, is_valid=False, errors=errors, warnings=warnings)

    stripped = content.lstrip()
    if not stripped.startswith("#"):
        errors.append("Generated Markdown must start with a heading.")

    if required_sections:
        missing_sections = _missing_sections(content, required_sections)
        if missing_sections:
            errors.append(
                "Generated Markdown is missing required sections: "
                + ", ".join(missing_sections)
            )

    warnings.extend(_detect_open_question_warnings(content))
    if "{{" in content or "}}" in content:
        warnings.append("Generated Markdown contains unresolved placeholder markers.")

    return _result(path=None, is_valid=not errors, errors=errors, warnings=warnings)


def validate_generated_markdown(
    content: str, required_sections: list[str] | None = None
) -> dict[str, Any]:
    return validate_markdown_content(content, required_sections=required_sections)


def validate_markdown_file(
    path: PathValue, required_sections: list[str] | None = None
) -> dict[str, Any]:
    try:
        file_path = _as_path(path)
    except ValueError as error:
        return _result(path=path, is_valid=False, errors=[str(error)], warnings=[])

    if not file_path.exists():
        return _result(
            file_path,
            False,
            [f"Markdown file does not exist: {file_path}"],
            [],
        )
    if not file_path.is_file():
        return _result(
            file_path,
            False,
            [f"Markdown path is not a file: {file_path}"],
            [],
        )
    if file_path.suffix.lower() != ".md":
        return _result(
            file_path,
            False,
            [f"Markdown file must use a .md extension: {file_path}"],
            [],
        )

    try:
        content = file_path.read_text(encoding="utf-8")
    except OSError as error:
        return _result(file_path, False, [f"Markdown file could not be read: {error}"], [])

    result = validate_markdown_content(content, required_sections=required_sections)
    result["path"] = str(file_path)
    return result


def _result(
    path: Any, is_valid: bool, errors: list[str], warnings: list[str]
) -> dict[str, Any]:
    if not is_valid:
        logger = get_workflow_logger()
        if logger.handlers:
            logger.error("validation_failure path=%s errors=%s", path, "; ".join(errors))
    return {
        "is_valid": is_valid,
        "path": str(path),
        "errors": errors,
        "warnings": warnings,
    }


def _as_path(path: PathValue) -> Path:
    if path is None:
        raise ValueError("Input path cannot be None.")
    if isinstance(path, str) and path.strip() == "":
        raise ValueError("Input path cannot be empty.")
    return Path(path).expanduser()


def _has_app_idea_heading(content: str) -> bool:
    return bool(re.search(r"^\s*#\s+app idea\s*$", content, flags=re.IGNORECASE | re.MULTILINE))


def _extract_meaningful_text(content: str) -> str:
    text = re.sub(r"```.*?```", " ", content, flags=re.DOTALL)
    text = re.sub(r"`[^`]*`", " ", text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", " ", text, flags=re.MULTILINE)
    text = re.sub(r"^\s*[-*+]\s+", " ", text, flags=re.MULTILINE)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"[*_>#]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _is_meaningful_app_idea(text: str) -> bool:
    normalized = text.lower().strip()
    normalized = re.sub(r"\s+", " ", normalized)
    if normalized in VAGUE_INPUTS:
        return False

    words = re.findall(r"[a-z0-9']+", normalized)
    substantive_words = [
        word
        for word in words
        if word not in {"app", "application", "ai", "tool", "build", "make", "want"}
    ]

    return len(words) >= 10 and len(substantive_words) >= 5


def _missing_sections(content: str, required_sections: list[str]) -> list[str]:
    headings = _extract_headings(content)
    missing = []
    for section in required_sections:
        if not any(_heading_matches(heading, section) for heading in headings):
            missing.append(section)
    return missing


def _extract_headings(content: str) -> list[str]:
    headings: list[str] = []
    for line in _strip_code_fences(content).splitlines():
        match = re.match(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(2).strip().rstrip("#").strip())
    return headings


def _strip_code_fences(content: str) -> str:
    return re.sub(r"```.*?```", " ", content, flags=re.DOTALL)


def _heading_matches(heading: str, expected: str) -> bool:
    normalized_heading = re.sub(r"\s+", " ", heading).strip().lower()
    normalized_expected = re.sub(r"\s+", " ", expected).strip().lower()
    return normalized_heading == normalized_expected


def _detect_open_question_warnings(content: str) -> list[str]:
    warnings: list[str] = []
    lowered = content.lower()
    if "open questions" in lowered:
        warnings.append(
            "Generated Markdown includes an 'Open Questions' section. "
            "Review unresolved items before using downstream."
        )
    if re.search(r"^\s*[-*+]\s*(todo|tbd|tba)\b", lowered, flags=re.MULTILINE):
        warnings.append("Generated Markdown includes TODO/TBD items.")
    return warnings
