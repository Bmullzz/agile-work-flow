"""Generate navigation files for a completed workflow output package."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from scripts.markdown_writer import write_markdown
from scripts.models import WorkflowStep


@dataclass
class IndexWriteResult:
    readme_path: Path
    project_context_path: Path
    warnings: list[str] = field(default_factory=list)


class IndexWriteError(RuntimeError):
    """Raised when output index files cannot be written."""


class IndexWriter:
    def write_indexes(
        self,
        output_root: str | Path,
        workflow_steps: Iterable[WorkflowStep],
        run_metadata: dict[str, Any] | None = None,
    ) -> IndexWriteResult:
        output_directory = Path(output_root)
        steps = list(workflow_steps)
        metadata = run_metadata or {}
        warnings: list[str] = []

        existing_steps = []
        for step in steps:
            output_path = output_directory / step.output_path
            if output_path.exists():
                existing_steps.append(step)
            else:
                warnings.append(f"Missing optional output skipped: {step.output_path}")

        try:
            readme_path = write_markdown(
                output_directory,
                "README.md",
                self._render_readme(existing_steps, metadata, warnings),
                overwrite=True,
            )
            project_context_path = write_markdown(
                output_directory,
                "project-context.md",
                self._render_project_context(existing_steps, metadata, warnings),
                overwrite=True,
            )
        except Exception as error:
            raise IndexWriteError(f"Failed to write output indexes: {error}") from error

        return IndexWriteResult(
            readme_path=readme_path,
            project_context_path=project_context_path,
            warnings=warnings,
        )

    def _render_readme(
        self,
        workflow_steps: list[WorkflowStep],
        metadata: dict[str, Any],
        warnings: list[str],
    ) -> str:
        lines = [
            "# AI Agile Workflow Output",
            "",
            "This folder contains generated planning documents for the workflow run.",
            "",
        ]
        lines.extend(_render_metadata(metadata))
        lines.extend(
            [
                "## Recommended Implementation Path",
                "",
                "1. Review the product and technical foundation documents.",
                "2. Read the phased roadmap and dependency analysis.",
                "3. Use the coding-agent prompts to implement stories in order.",
                "4. Validate work against the QA validation plan.",
                "",
            ]
        )

        coding_agent_step = _find_step(workflow_steps, "12-coding-agent-prompts")
        if coding_agent_step is not None:
            lines.extend(
                [
                    "## Coding-Agent Prompts",
                    "",
                    f"- [Coding-Agent Prompts]({_markdown_link(coding_agent_step.output_path)})",
                    "",
                ]
            )

        lines.extend(["## Generated Documents", ""])
        for step in workflow_steps:
            lines.append(f"- [{step.name}]({_markdown_link(step.output_path)})")
        lines.append("")

        if warnings:
            lines.extend(["## Warnings", ""])
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    def _render_project_context(
        self,
        workflow_steps: list[WorkflowStep],
        metadata: dict[str, Any],
        warnings: list[str],
    ) -> str:
        lines = [
            "# Project Context",
            "",
            "Generated context index for this AI Agile Workflow output package.",
            "",
        ]
        lines.extend(_render_metadata(metadata))
        lines.extend(["## Document Map", ""])
        for step in workflow_steps:
            lines.append(f"- {step.step_id}: [{step.name}]({_markdown_link(step.output_path)})")
        lines.append("")

        lines.extend(
            [
                "## Implementation Guidance",
                "",
                "Start with the roadmap, then follow dependency order through the coding-agent prompts.",
                "",
            ]
        )

        if warnings:
            lines.extend(["## Warnings", ""])
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)


def _render_metadata(metadata: dict[str, Any]) -> list[str]:
    generated_at = metadata.get("generated_at") or datetime.now(timezone.utc).isoformat()
    lines = [
        "## Run Metadata",
        "",
        f"- Generated at: {generated_at}",
    ]
    for key in sorted(metadata):
        if key == "generated_at":
            continue
        lines.append(f"- {key.replace('_', ' ').title()}: {metadata[key]}")
    lines.extend(["", ""])
    return lines


def _find_step(workflow_steps: list[WorkflowStep], step_id: str) -> WorkflowStep | None:
    for step in workflow_steps:
        if step.step_id == step_id:
            return step
    return None


def _markdown_link(path: Path) -> str:
    return path.as_posix()
