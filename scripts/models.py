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

    def to_dict(self) -> dict:
        return {
            "step_number": self.step_number,
            "step_id": self.step_id,
            "name": self.name,
            "prompt_template_path": str(self.prompt_template_path),
            "output_path": str(self.output_path),
            "depends_on_step_ids": list(self.depends_on_step_ids),
            "required_sections": list(self.required_sections),
            "blocks_step_ids": list(self.blocks_step_ids),
            "status": self.status,
            "review_status": self.review_status,
            "can_skip": self.can_skip,
            "stale": self.stale,
        }


@dataclass
class WorkflowState:
    project_name: str
    input_file: str
    output_folder: str
    workflow_status: str = "not_started"
    completed_steps: list[str] = field(default_factory=list)
    output_files: dict[str, str] = field(default_factory=dict)
    failed_step: str | None = None
    current_step: str | None = None
    next_step: str | None = None
    approved_steps: list[str] = field(default_factory=list)
    pending_review_step: str | None = None
    stale_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "project_name": self.project_name,
            "input_file": self.input_file,
            "output_folder": self.output_folder,
            "workflow_status": self.workflow_status,
            "completed_steps": list(self.completed_steps),
            "output_files": dict(self.output_files),
            "failed_step": self.failed_step,
            "current_step": self.current_step,
            "next_step": self.next_step,
            "approved_steps": list(self.approved_steps),
            "pending_review_step": self.pending_review_step,
            "stale_steps": list(self.stale_steps),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WorkflowState":
        return cls(
            project_name=data["project_name"],
            input_file=data["input_file"],
            output_folder=data["output_folder"],
            workflow_status=data.get("workflow_status", "not_started"),
            completed_steps=list(data.get("completed_steps", [])),
            output_files=dict(data.get("output_files", {})),
            failed_step=data.get("failed_step"),
            current_step=data.get("current_step"),
            next_step=data.get("next_step"),
            approved_steps=list(data.get("approved_steps", [])),
            pending_review_step=data.get("pending_review_step"),
            stale_steps=list(data.get("stale_steps", [])),
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
