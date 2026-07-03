"""Shared data models for workflow execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Union


PathValue = Union[str, Path]


@dataclass
class WorkflowStep:
    step_number: int
    step_id: str
    name: str
    prompt_template_path: PathValue
    output_path: PathValue
    depends_on_step_ids: list[str] = field(default_factory=list)
    required_sections: list[str] = field(default_factory=list)
    blocks_step_ids: list[str] = field(default_factory=list)
    status: str = "pending"
    review_status: str = "not_required"
    can_skip: bool = False
    stale: bool = False

    def __post_init__(self) -> None:
        if self.step_number < 0:
            raise ValueError("step_number must be zero or greater.")
        self.step_id = _require_non_empty_string(self.step_id, "step_id")
        self.name = _require_non_empty_string(self.name, "name")
        self.prompt_template_path = _require_path(
            self.prompt_template_path, "prompt_template_path"
        )
        self.output_path = _require_path(self.output_path, "output_path")
        self.depends_on_step_ids = _validate_string_list(
            self.depends_on_step_ids, "depends_on_step_ids"
        )
        self.required_sections = _validate_string_list(
            self.required_sections, "required_sections"
        )
        self.blocks_step_ids = _validate_string_list(
            self.blocks_step_ids, "blocks_step_ids"
        )


def _require_non_empty_string(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value


def _require_path(value: PathValue, field_name: str) -> Path:
    if value is None:
        raise ValueError(f"{field_name} cannot be None.")
    if isinstance(value, str) and not value.strip():
        raise ValueError(f"{field_name} cannot be empty.")
    return Path(value)


def _validate_string_list(value: list[str], field_name: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field_name} must be a list of strings.")
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field_name} must contain only non-empty strings.")
    return list(value)
