"""Core workflow runner integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from scripts.context_builder import build_context
from scripts.index_writer import IndexWriter
from scripts.llm_client import LLMClient
from scripts.markdown_writer import write_markdown
from scripts.models import WorkflowStep
from scripts.prompt_loader import render_prompt_file
from scripts.validators import validate_generated_markdown, validate_input_file


PromptRenderer = Callable[[Path, dict[str, str]], str]
ContextBuilder = Callable[
    [WorkflowStep, Path, Path, Iterable[WorkflowStep]], dict[str, str]
]
MarkdownWriter = Callable[[Path, Path, str, bool], Path]
InputValidator = Callable[[Path], dict[str, Any]]
OutputValidator = Callable[[str], dict[str, Any]]


class WorkflowRunError(RuntimeError):
    """Raised when a workflow step cannot complete."""


@dataclass
class WorkflowRunResult:
    completed_step_ids: list[str] = field(default_factory=list)
    output_paths: dict[str, Path] = field(default_factory=dict)
    failed_step_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    index_paths: dict[str, Path] = field(default_factory=dict)
    index_warnings: list[str] = field(default_factory=list)


class WorkflowRunner:
    def __init__(
        self,
        config: dict[str, Any],
        workflow_steps: list[WorkflowStep],
        prompt_loader: PromptRenderer = render_prompt_file,
        context_builder: ContextBuilder = build_context,
        llm_client: LLMClient | None = None,
        markdown_writer: MarkdownWriter = write_markdown,
        input_validator: InputValidator = validate_input_file,
        output_validator: OutputValidator = validate_generated_markdown,
        index_writer: IndexWriter | None = None,
    ) -> None:
        if llm_client is None:
            raise ValueError("llm_client is required.")

        self.config = config or {}
        self.workflow_steps = list(workflow_steps)
        self.prompt_loader = prompt_loader
        self.context_builder = context_builder
        self.llm_client = llm_client
        self.markdown_writer = markdown_writer
        self.input_validator = input_validator
        self.output_validator = output_validator
        self.index_writer = index_writer or IndexWriter()

    def run(self, input_path: str | Path, output_root: str | Path) -> WorkflowRunResult:
        input_file = Path(input_path)
        output_directory = Path(output_root)
        result = WorkflowRunResult()
        completed_steps: list[WorkflowStep] = []
        completed_step_ids: set[str] = set()

        input_validation = self.input_validator(input_file)
        if not input_validation["is_valid"]:
            self._fail(
                result,
                "input",
                "Input validation failed: " + "; ".join(input_validation["errors"]),
            )

        overwrite = bool(self.config.get("output", {}).get("overwrite", False))

        for step in self.workflow_steps:
            print(f"[{step.step_id}] Starting {step.name}")
            try:
                self._check_dependencies(step, completed_step_ids)
                context = self.context_builder(
                    step, input_file, output_directory, completed_steps
                )
                prompt = self.prompt_loader(step.prompt_template_path, context)
                generated_markdown = self.llm_client.generate(prompt)
                self._validate_generated_markdown(step, generated_markdown)
                output_path = self.markdown_writer(
                    output_directory,
                    step.output_path,
                    generated_markdown,
                    overwrite,
                )
            except Exception as error:
                message = f"Step {step.step_id} failed: {error}"
                if self._stop_on_failure():
                    self._fail(result, step.step_id, message)
                result.failed_step_id = step.step_id
                result.errors.append(message)
                print(message)
                continue

            completed_steps.append(step)
            completed_step_ids.add(step.step_id)
            result.completed_step_ids.append(step.step_id)
            result.output_paths[step.step_id] = output_path
            print(f"[{step.step_id}] Wrote {output_path}")

        if result.failed_step_id is None:
            try:
                index_result = self.index_writer.write_indexes(
                    output_directory,
                    self.workflow_steps,
                    run_metadata={
                        "generated_at": "not recorded",
                        "completed_steps": len(result.completed_step_ids),
                    },
                )
            except Exception as error:
                message = f"Index generation failed: {error}"
                self._fail(result, "index", message)

            result.index_paths = {
                "README": index_result.readme_path,
                "PROJECT_CONTEXT": index_result.project_context_path,
            }
            result.index_warnings = list(index_result.warnings)
            for warning in result.index_warnings:
                print(f"[index] Warning: {warning}")
            print(f"[index] Wrote {index_result.readme_path}")
            print(f"[index] Wrote {index_result.project_context_path}")

        return result

    def _check_dependencies(
        self, step: WorkflowStep, completed_step_ids: set[str]
    ) -> None:
        missing = [
            step_id
            for step_id in step.depends_on_step_ids
            if step_id not in completed_step_ids
        ]
        if missing:
            raise WorkflowRunError(
                f"Missing completed dependencies for {step.step_id}: "
                + ", ".join(missing)
            )

    def _validate_generated_markdown(self, step: WorkflowStep, content: str) -> None:
        validation = self.output_validator(content)
        if not validation["is_valid"]:
            raise WorkflowRunError(
                f"Invalid generated Markdown for {step.step_id}: "
                + "; ".join(validation["errors"])
            )

    def _stop_on_failure(self) -> bool:
        return bool(self.config.get("workflow", {}).get("stop_on_failure", True))

    def _fail(
        self, result: WorkflowRunResult, step_id: str, message: str
    ) -> None:
        result.failed_step_id = step_id
        result.errors.append(message)
        raise WorkflowRunError(message)
