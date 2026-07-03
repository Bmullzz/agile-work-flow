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
from scripts.workflow_state import (
    WorkflowState,
    WorkflowStateError,
    create_initial_state,
    load_state,
    mark_step_completed,
    mark_step_failed,
    mark_step_started,
    save_state,
    state_file_path,
)


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
    state_path: Optional[Path] = None


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
        state_path = state_file_path(output_directory)
        result.state_path = state_path

        input_validation = self.input_validator(input_file)
        if not input_validation["is_valid"]:
            self._fail(
                result,
                "input",
                "Input validation failed: " + "; ".join(input_validation["errors"]),
            )

        overwrite = bool(self.config.get("output", {}).get("overwrite", False))
        state = self._load_or_create_state(input_file, output_directory, state_path)
        self._save_state_safely(state, state_path)

        for index, step in enumerate(self.workflow_steps):
            print(f"[{step.step_id}] Starting {step.name}")
            try:
                self._check_dependencies(step, completed_step_ids)
                mark_step_started(
                    state,
                    step.step_id,
                    next_step=self._next_step_id(index),
                )
                self._save_state_safely(state, state_path)
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
                mark_step_failed(state, step.step_id)
                self._save_state_safely(state, state_path)
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
            mark_step_completed(
                state,
                step.step_id,
                output_path,
                next_step=self._next_step_id(index),
            )
            self._save_state_safely(state, state_path)
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
            state.output_files["README"] = str(index_result.readme_path)
            state.output_files["PROJECT_CONTEXT"] = str(
                index_result.project_context_path
            )
            state.workflow_status = "completed"
            state.current_step = None
            state.next_step = None
            self._save_state_safely(state, state_path)
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

    def _load_or_create_state(
        self, input_file: Path, output_directory: Path, path: Path
    ) -> WorkflowState:
        if path.exists():
            return load_state(path)

        project_name = output_directory.name or "workflow-output"
        next_step = self.workflow_steps[0].step_id if self.workflow_steps else None
        return create_initial_state(
            project_name=project_name,
            input_file=input_file,
            output_folder=output_directory,
            next_step=next_step,
        )

    def _save_state_safely(self, state: WorkflowState, path: Path) -> None:
        try:
            save_state(state, path)
        except WorkflowStateError as error:
            raise WorkflowRunError(f"State write failed: {error}") from error

    def _next_step_id(self, index: int) -> str | None:
        next_index = index + 1
        if next_index >= len(self.workflow_steps):
            return None
        return self.workflow_steps[next_index].step_id

    def _fail(
        self, result: WorkflowRunResult, step_id: str, message: str
    ) -> None:
        result.failed_step_id = step_id
        result.errors.append(message)
        raise WorkflowRunError(message)
