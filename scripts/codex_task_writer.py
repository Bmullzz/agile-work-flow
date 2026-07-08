"""Write Codex-ready task packets for workflow steps."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from scripts.file_utils import ensure_directory, write_text_file
from scripts.models import WorkflowStep


@dataclass
class CodexTaskWriteResult:
    """Paths written for a Codex task packet."""

    task_directory: Path
    prompt_path: Path
    context_path: Path
    expected_output_path: Path
    target_file_path: Path
    instructions_path: Path


class CodexTaskWriter:
    """Create self-contained task packets that can be used manually in Codex."""

    def write_task_packet(
        self,
        output_root: str | Path,
        step: WorkflowStep,
        prompt: str,
        context: dict[str, Any],
        target_output_path: str | Path,
        task_export_dir: str | Path = "99-meta/codex-tasks",
        overwrite: bool = False,
    ) -> CodexTaskWriteResult:
        output_directory = Path(output_root)
        task_directory = output_directory / Path(task_export_dir) / step.step_id
        ensure_directory(task_directory)

        target_path = Path(target_output_path)
        prompt_path = write_text_file(
            task_directory / "prompt.md",
            self._render_prompt(step, prompt),
            overwrite=overwrite,
        )
        context_path = write_text_file(
            task_directory / "context.md",
            self._render_context(step, context),
            overwrite=overwrite,
        )
        expected_output_path = write_text_file(
            task_directory / "expected-output.md",
            self._render_expected_output(step),
            overwrite=overwrite,
        )
        target_file_path = write_text_file(
            task_directory / "target-file.txt",
            f"{target_path}\n",
            overwrite=overwrite,
        )
        instructions_path = write_text_file(
            task_directory / "instructions.md",
            self._render_instructions(step),
            overwrite=overwrite,
        )

        return CodexTaskWriteResult(
            task_directory=task_directory,
            prompt_path=prompt_path,
            context_path=context_path,
            expected_output_path=expected_output_path,
            target_file_path=target_file_path,
            instructions_path=instructions_path,
        )

    def _render_prompt(self, step: WorkflowStep, prompt: str) -> str:
        return "\n".join(
            [
                f"# Codex Prompt: {step.name}",
                "",
                f"- Step ID: {step.step_id}",
                f"- Step name: {step.name}",
                "",
                "## Rendered Workflow Prompt",
                "",
                prompt.strip(),
                "",
            ]
        )

    def _render_context(self, step: WorkflowStep, context: dict[str, Any]) -> str:
        lines = [
            f"# Codex Task Context: {step.name}",
            "",
            f"- Step ID: {step.step_id}",
            f"- Step name: {step.name}",
            f"- Dependencies: {_format_list(step.depends_on_step_ids)}",
            "",
            "## App Idea",
            "",
            str(context.get("APP_IDEA", "Not provided.")).strip(),
            "",
        ]

        dependency_sections = _dependency_context_sections(context)
        if dependency_sections:
            lines.extend(["## Dependency Outputs", ""])
            for label, content in dependency_sections:
                lines.extend([f"### {label}", "", content.strip(), ""])
        else:
            lines.extend(["## Dependency Outputs", "", "No dependency outputs are required.", ""])

        project_context = str(context.get("PROJECT_CONTEXT", "")).strip()
        if project_context:
            lines.extend(["## Project Context", "", project_context, ""])

        workflow_state = str(context.get("WORKFLOW_STATE_SUMMARY", "")).strip()
        if workflow_state:
            lines.extend(["## Current Workflow State", "", workflow_state, ""])
        else:
            lines.extend(
                [
                    "## Current Workflow State",
                    "",
                    "No workflow state summary was provided.",
                    "",
                ]
            )

        return "\n".join(lines)

    def _render_expected_output(self, step: WorkflowStep) -> str:
        lines = [
            f"# Expected Output: {step.name}",
            "",
            f"- Step ID: {step.step_id}",
            f"- Step name: {step.name}",
            f"- Output path: {step.output_path}",
            "",
            "## Required Sections",
            "",
        ]
        if step.required_sections:
            for section in step.required_sections:
                lines.append(f"- {section}")
        else:
            lines.append("- No step-specific required sections configured.")

        lines.extend(
            [
                "",
                "## Validation Rules",
                "",
                "- The final output must be Markdown only.",
                "- The final output must start with a Markdown heading.",
                "- The final output must include every required section listed above.",
                "- Do not include API keys, credentials, or local secrets.",
                "",
            ]
        )
        return "\n".join(lines)

    def _render_instructions(self, step: WorkflowStep) -> str:
        return "\n".join(
            [
                "# Codex Task Instructions",
                "",
                "Open this task folder in Codex.",
                "",
                "Ask Codex to read `prompt.md`, `context.md`, and `expected-output.md`.",
                "",
                "Codex should create or update the file listed in `target-file.txt`.",
                "",
                "The final output must be Markdown only.",
                "",
                f"Step ID: `{step.step_id}`",
                f"Step name: {step.name}",
                "",
            ]
        )


def _dependency_context_sections(context: dict[str, Any]) -> list[tuple[str, str]]:
    dependency_keys = [
        "APP_INTAKE",
        "PRODUCT_VISION",
        "TECH_STACK",
        "SYSTEM_ARCHITECTURE",
        "TECHNICAL_STORIES",
        "DEPENDENCY_ANALYSIS",
        "PHASED_ROADMAP",
    ]
    sections: list[tuple[str, str]] = []
    for key in dependency_keys:
        value = str(context.get(key, "")).strip()
        if value:
            sections.append((key.replace("_", " ").title(), value))
    return sections


def _format_list(values: list[str]) -> str:
    return ", ".join(values) if values else "none"
