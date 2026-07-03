"""Prompt template loading and rendering helpers."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Union


PathValue = Union[str, Path]
PLACEHOLDER_PATTERN = re.compile(r"{{\s*([A-Z][A-Z0-9_]*)\s*}}")


class PromptTemplateError(ValueError):
    """Raised when a prompt template cannot be loaded or rendered."""


def load_prompt_template(path: PathValue) -> str:
    template_path = _as_path(path)
    if not template_path.exists():
        raise FileNotFoundError(f"Prompt template not found: {template_path}")
    if not template_path.is_file():
        raise PromptTemplateError(f"Prompt template path is not a file: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    if not content.strip():
        raise PromptTemplateError(f"Prompt template is empty: {template_path}")

    return content


def render_prompt(template: str, context: dict[str, Any]) -> str:
    if template is None or not template.strip():
        raise PromptTemplateError("Prompt template is empty.")

    context = context or {}
    placeholders = _find_placeholders(template)
    missing = sorted(
        placeholder
        for placeholder in placeholders
        if placeholder not in context or context[placeholder] is None
    )
    if missing:
        missing_list = ", ".join(missing)
        raise PromptTemplateError(f"Missing required prompt context: {missing_list}")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(context[key])

    return PLACEHOLDER_PATTERN.sub(replace, template)


def render_prompt_file(path: PathValue, context: dict[str, Any]) -> str:
    return render_prompt(load_prompt_template(path), context)


def _find_placeholders(template: str) -> set[str]:
    return set(PLACEHOLDER_PATTERN.findall(template))


def _as_path(path: PathValue) -> Path:
    if path is None:
        raise ValueError("Prompt template path cannot be None.")
    if isinstance(path, str) and path.strip() == "":
        raise ValueError("Prompt template path cannot be empty.")
    return Path(path).expanduser()
