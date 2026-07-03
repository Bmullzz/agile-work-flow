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
from scripts.review_gate import ReviewDecision, ReviewGate
from scripts.validators import validate_generated_markdown, validate_input_file
from scripts.workflow_state import (
    WorkflowState,
    WorkflowStateError,
    create_initial_state,
    load_state,
    mark_step_completed,
    mark_downstream_steps_stale,
    mark_step_failed,
    mark_step_approved,
    mark_step_skipped,
    mark_step_started,
    mark_workflow_quit,
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
    skipped_step_ids: list[str] = field(default_factory=list)
    output_paths: dict[str, Path] = field(default_factory=dict)
    failed_step_id: Optional[str] = None
    errors: list[str] = field(default_factory=list)
    index_paths: dict[str, Path] = field(default_factory=dict)
    index_warnings: list[str] = field(default_factory=list)
    state_path: Optional[Path] = None
    quit_requested: bool = False


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
        review_gate: ReviewGate | None = None,
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
        self.review_gate = review_gate or ReviewGate()

    def run(
        self,
        input_path: str | Path,
        output_root: str | Path,
        resume: bool = False,
        step_id: str | None = None,
        from_step_id: str | None = None,
        review: bool | None = None,
    ) -> WorkflowRunResult:
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
        review_enabled = self._review_enabled(review)
        state = self._load_or_create_state(input_file, output_directory, state_path)
        self._save_state_safely(state, state_path)
        steps_to_run = self._select_steps(
            state,
            output_directory,
            resume=resume,
            step_id=step_id,
            from_step_id=from_step_id,
        )
        self._seed_completed_dependencies(
            steps_to_run,
            output_directory,
            completed_steps,
            completed_step_ids,
        )

        for index, step in enumerate(steps_to_run):
            print(f"[{step.step_id}] Starting {step.name}")
            try:
                self._check_dependencies(
                    step,
                    completed_step_ids,
                    state=state,
                    review_enabled=review_enabled,
                )
                mark_step_started(
                    state,
                    step.step_id,
                    next_step=self._next_step_id(steps_to_run, index),
                )
                self._save_state_safely(state, state_path)
                existing_output = output_directory / step.output_path
                if (
                    not overwrite
                    and step.step_id not in state.stale_steps
                    and self._is_existing_output_valid(step, output_directory)
                ):
                    result.skipped_step_ids.append(step.step_id)
                    self._record_step_success(
                        state,
                        result,
                        completed_steps,
                        completed_step_ids,
                        step,
                        existing_output,
                        self._next_step_id(steps_to_run, index),
                        skipped=True,
                    )
                    self._save_state_safely(state, state_path)
                    print(f"[{step.step_id}] Skipped existing valid output")
                    continue
                was_approved_before_generation = step.step_id in state.approved_steps
                output_path = self._generate_step_output(
                    step,
                    input_file,
                    output_directory,
                    completed_steps,
                    overwrite or step.step_id in state.stale_steps,
                )
                if was_approved_before_generation:
                    self._mark_downstream_stale(state, step)
                    self._save_state_safely(state, state_path)
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

            try:
                review_outcome = self._review_step_if_needed(
                    review_enabled,
                    step,
                    output_path,
                    input_file,
                    output_directory,
                    completed_steps,
                    overwrite,
                    state,
                    state_path,
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

            if review_outcome == ReviewDecision.QUIT:
                mark_workflow_quit(state, step.step_id)
                self._save_state_safely(state, state_path)
                result.quit_requested = True
                print(f"[{step.step_id}] Review requested quit.")
                return result

            self._record_step_success(
                state,
                result,
                completed_steps,
                completed_step_ids,
                step,
                output_path,
                self._next_step_id(steps_to_run, index),
                skipped=review_outcome == ReviewDecision.SKIP,
            )
            self._save_state_safely(state, state_path)
            print(f"[{step.step_id}] Wrote {output_path}")

        if result.failed_step_id is None and not result.quit_requested:
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
            state.workflow_status = "stale" if state.stale_steps else "completed"
            state.current_step = None
            state.next_step = state.stale_steps[0] if state.stale_steps else None
            self._save_state_safely(state, state_path)
            for warning in result.index_warnings:
                print(f"[index] Warning: {warning}")
            print(f"[index] Wrote {index_result.readme_path}")
            print(f"[index] Wrote {index_result.project_context_path}")

        return result

    def _check_dependencies(
        self,
        step: WorkflowStep,
        completed_step_ids: set[str],
        state: WorkflowState | None = None,
        review_enabled: bool = False,
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
        if state is not None:
            stale = [
                step_id
                for step_id in step.depends_on_step_ids
                if step_id in state.stale_steps
            ]
            if stale:
                raise WorkflowRunError(
                    f"Stale dependencies for {step.step_id}: " + ", ".join(stale)
                )
        if review_enabled and state is not None:
            unapproved = [
                step_id
                for step_id in step.depends_on_step_ids
                if step_id not in state.approved_steps
            ]
            if unapproved:
                raise WorkflowRunError(
                    f"Unapproved dependencies for {step.step_id}: "
                    + ", ".join(unapproved)
                )

    def _select_steps(
        self,
        state: WorkflowState,
        output_directory: Path,
        resume: bool,
        step_id: str | None,
        from_step_id: str | None,
    ) -> list[WorkflowStep]:
        if step_id and from_step_id:
            raise WorkflowRunError("Use either --step or --from-step, not both.")

        if step_id:
            return [self._get_step_by_id(step_id)]

        if from_step_id:
            start_index = self._get_step_index(from_step_id)
            return self.workflow_steps[start_index:]

        if resume:
            resume_step_id = state.next_step or self._first_incomplete_step_id(
                state, output_directory
            )
            if resume_step_id is None:
                print("[resume] No incomplete workflow steps found.")
                return []
            start_index = self._get_step_index(resume_step_id)
            print(f"[resume] Continuing from {resume_step_id}")
            return self.workflow_steps[start_index:]

        return list(self.workflow_steps)

    def _seed_completed_dependencies(
        self,
        steps_to_run: list[WorkflowStep],
        output_directory: Path,
        completed_steps: list[WorkflowStep],
        completed_step_ids: set[str],
    ) -> None:
        if not steps_to_run:
            return
        first_index = self._get_step_index(steps_to_run[0].step_id)
        for step in self.workflow_steps[:first_index]:
            if self._is_existing_output_valid(step, output_directory):
                completed_steps.append(step)
                completed_step_ids.add(step.step_id)

    def _first_incomplete_step_id(
        self, state: WorkflowState, output_directory: Path
    ) -> str | None:
        completed_step_ids = set(state.completed_steps)
        for step in self.workflow_steps:
            if step.step_id in state.stale_steps:
                return step.step_id
            if step.step_id not in completed_step_ids:
                return step.step_id
            if not self._is_existing_output_valid(step, output_directory):
                return step.step_id
        return None

    def _get_step_by_id(self, step_id: str) -> WorkflowStep:
        for step in self.workflow_steps:
            if step.step_id == step_id:
                return step
        raise WorkflowRunError(f"Unknown workflow step ID: {step_id}")

    def _get_step_index(self, step_id: str) -> int:
        for index, step in enumerate(self.workflow_steps):
            if step.step_id == step_id:
                return index
        raise WorkflowRunError(f"Unknown workflow step ID: {step_id}")

    def _validate_generated_markdown(self, step: WorkflowStep, content: str) -> None:
        validation = self.output_validator(content)
        if not validation["is_valid"]:
            raise WorkflowRunError(
                f"Invalid generated Markdown for {step.step_id}: "
                + "; ".join(validation["errors"])
            )

    def _generate_step_output(
        self,
        step: WorkflowStep,
        input_file: Path,
        output_directory: Path,
        completed_steps: list[WorkflowStep],
        overwrite: bool,
    ) -> Path:
        context = self.context_builder(
            step, input_file, output_directory, completed_steps
        )
        prompt = self.prompt_loader(step.prompt_template_path, context)
        generated_markdown = self.llm_client.generate(prompt)
        self._validate_generated_markdown(step, generated_markdown)
        return self.markdown_writer(
            output_directory,
            step.output_path,
            generated_markdown,
            overwrite,
        )

    def _review_step_if_needed(
        self,
        review_enabled: bool,
        step: WorkflowStep,
        output_path: Path,
        input_file: Path,
        output_directory: Path,
        completed_steps: list[WorkflowStep],
        overwrite: bool,
        state: WorkflowState,
        state_path: Path,
    ) -> ReviewDecision | None:
        if not review_enabled:
            return None

        state.pending_review_step = step.step_id
        self._save_state_safely(state, state_path)

        while True:
            decision = self.review_gate.review(step, output_path)
            if decision == ReviewDecision.REGENERATE:
                output_path = self._generate_step_output(
                    step,
                    input_file,
                    output_directory,
                    completed_steps,
                    overwrite=True,
                )
                if step.step_id in state.approved_steps:
                    self._mark_downstream_stale(state, step)
                    self._save_state_safely(state, state_path)
                continue
            if decision == ReviewDecision.EDIT:
                if step.step_id in state.approved_steps:
                    self._mark_downstream_stale(state, step)
                mark_step_approved(state, step.step_id)
                self._save_state_safely(state, state_path)
                return decision
            if decision == ReviewDecision.APPROVE:
                mark_step_approved(state, step.step_id)
                self._save_state_safely(state, state_path)
                return decision
            if decision == ReviewDecision.SKIP:
                mark_step_approved(state, step.step_id)
                self._save_state_safely(state, state_path)
                return decision
            if decision == ReviewDecision.QUIT:
                return decision

    def _record_step_success(
        self,
        state: WorkflowState,
        result: WorkflowRunResult,
        completed_steps: list[WorkflowStep],
        completed_step_ids: set[str],
        step: WorkflowStep,
        output_path: Path,
        next_step_id: str | None,
        skipped: bool = False,
    ) -> None:
        completed_steps.append(step)
        completed_step_ids.add(step.step_id)
        result.completed_step_ids.append(step.step_id)
        result.output_paths[step.step_id] = output_path
        if skipped:
            if step.step_id not in result.skipped_step_ids:
                result.skipped_step_ids.append(step.step_id)
            mark_step_skipped(state, step.step_id, output_path, next_step=next_step_id)
        else:
            mark_step_completed(state, step.step_id, output_path, next_step=next_step_id)

    def _stop_on_failure(self) -> bool:
        return bool(self.config.get("workflow", {}).get("stop_on_failure", True))

    def _review_enabled(self, override: bool | None) -> bool:
        if override is not None:
            return override
        return bool(self.config.get("workflow", {}).get("default_review", False))

    def _mark_downstream_stale(
        self, state: WorkflowState, step: WorkflowStep
    ) -> list[str]:
        stale_step_ids = mark_downstream_steps_stale(
            state, step.step_id, self.workflow_steps
        )
        show_stale_steps = getattr(self.review_gate, "show_stale_steps", None)
        if callable(show_stale_steps):
            show_stale_steps(step, stale_step_ids)
        elif stale_step_ids:
            print(
                f"[{step.step_id}] Downstream documents marked stale: "
                + ", ".join(stale_step_ids)
            )
        return stale_step_ids

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

    def _next_step_id(self, steps: list[WorkflowStep], index: int) -> str | None:
        next_index = index + 1
        if next_index >= len(steps):
            return None
        return steps[next_index].step_id

    def _is_existing_output_valid(self, step: WorkflowStep, output_directory: Path) -> bool:
        output_path = output_directory / step.output_path
        if not output_path.exists() or not output_path.is_file():
            return False
        try:
            content = output_path.read_text(encoding="utf-8")
        except OSError:
            return False
        return bool(self.output_validator(content)["is_valid"])

    def _fail(
        self, result: WorkflowRunResult, step_id: str, message: str
    ) -> None:
        result.failed_step_id = step_id
        result.errors.append(message)
        raise WorkflowRunError(message)
