"""Build prompt context for a workflow step."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Union

from scripts.file_utils import read_markdown_file
from scripts.models import WorkflowStep
from scripts.workflow_steps import get_step_by_id


PathValue = Union[str, Path]

DEPENDENCY_PLACEHOLDERS = {
    "00-app-intake": "APP_INTAKE",
    "01-product-vision": "PRODUCT_VISION",
    "02-tech-stack": "TECH_STACK",
    "03-system-architecture": "SYSTEM_ARCHITECTURE",
    "07-technical-stories": "TECHNICAL_STORIES",
    "09-dependency-analysis": "DEPENDENCY_ANALYSIS",
    "10-phased-roadmap": "PHASED_ROADMAP",
}


class ContextBuildError(RuntimeError):
    """Raised when a workflow step context cannot be built."""


def build_context(
    step: WorkflowStep,
    input_path: PathValue,
    output_root: PathValue,
    completed_steps: Union[Iterable[WorkflowStep], dict[str, WorkflowStep]],
) -> dict[str, str]:
    input_file = Path(input_path)
    output_directory = Path(output_root)
    completed_by_id = _completed_steps_by_id(completed_steps)

    context = {
        "APP_IDEA": read_markdown_file(input_file),
        "PROJECT_CONTEXT": "",
    }

    project_context_path = input_file.parent / "project-context.md"
    project_context_parts = []
    if project_context_path.exists():
        project_context_parts.append(
            _format_context_document(
                "Project Context", read_markdown_file(project_context_path)
            )
        )

    for dependency_id in step.depends_on_step_ids:
        dependency_step = completed_by_id.get(dependency_id) or get_step_by_id(
            dependency_id
        )
        dependency_content = _read_dependency_output(
            dependency_step, output_directory, step.step_id
        )
        placeholder = DEPENDENCY_PLACEHOLDERS.get(dependency_id)
        if placeholder:
            context[placeholder] = dependency_content
        else:
            project_context_parts.append(
                _format_context_document(dependency_step.name, dependency_content)
            )

    if project_context_parts:
        context["PROJECT_CONTEXT"] = "\n\n".join(project_context_parts)

    return context


def _completed_steps_by_id(
    completed_steps: Union[Iterable[WorkflowStep], dict[str, WorkflowStep]]
) -> dict[str, WorkflowStep]:
    if isinstance(completed_steps, dict):
        return dict(completed_steps)
    return {step.step_id: step for step in completed_steps}


def _read_dependency_output(
    dependency_step: WorkflowStep, output_root: Path, current_step_id: str
) -> str:
    dependency_output_path = output_root / dependency_step.output_path
    if not dependency_output_path.exists():
        raise ContextBuildError(
            "Missing required dependency output for "
            f"{current_step_id}: {dependency_step.step_id} at {dependency_output_path}"
        )
    return read_markdown_file(dependency_output_path)


def _format_context_document(title: str, content: str) -> str:
    return f"## {title}\n\n{content.strip()}"
