"""Core workflow runner integration."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import logging
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from scripts.context_builder import build_context
from scripts.backends.base import GenerationBackend
from scripts.index_writer import IndexWriter
from scripts.logger import get_workflow_logger, redact_secrets, setup_workflow_logging
from scripts.markdown_writer import write_markdown
from scripts.models import WorkflowStep
from scripts.prompt_loader import render_prompt_file
from scripts.review_gate import ReviewDecision, ReviewGate
from scripts.validators import validate_input_file, validate_markdown_content
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
MarkdownWriter = Callable[..., Path]
InputValidator = Callable[[Path], dict[str, Any]]
OutputValidator = Callable[..., dict[str, Any]]


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
        generation_backend: GenerationBackend | None = None,
        llm_client: Any | None = None,
        markdown_writer: MarkdownWriter = write_markdown,
        input_validator: InputValidator = validate_input_file,
        output_validator: OutputValidator = validate_markdown_content,
        index_writer: IndexWriter | None = None,
        review_gate: ReviewGate | None = None,
        logger: logging.Logger | None = None,
    ) -> None:
        if generation_backend is None and llm_client is None:
            raise ValueError("generation_backend is required.")

        self.config = config or {}
        self.workflow_steps = list(workflow_steps)
        self.prompt_loader = prompt_loader
        self.context_builder = context_builder
        self.generation_backend = generation_backend or _LLMClientBackendAdapter(llm_client)
        self.markdown_writer = markdown_writer
        self.input_validator = input_validator
        self.output_validator = output_validator
        self.fail_on_warnings = bool(
            self.config.get("workflow", {}).get("fail_on_warnings", False)
        )
        self.index_writer = index_writer or IndexWriter()
        self.review_gate = review_gate or ReviewGate(
            fail_on_warnings=self.fail_on_warnings
        )
        self.logger = logger or get_workflow_logger()
        self._generation_metadata_by_step: dict[str, dict[str, Any]] = {}

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
        self.logger, log_path = setup_workflow_logging(output_directory)
        self.logger.info(
            "workflow_start input=%s output=%s resume=%s step=%s from_step=%s",
            input_file,
            output_directory,
            resume,
            step_id,
            from_step_id,
        )
        self.logger.info("log_file path=%s", log_path)

        input_validation = self.input_validator(input_file)
        if not input_validation["is_valid"]:
            self.logger.error(
                "validation_failure step=input errors=%s",
                "; ".join(input_validation["errors"]),
            )
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
            self.logger.info("step_start step=%s name=%s", step.step_id, step.name)
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
                    self.logger.info(
                        "step_skip step=%s output=%s reason=existing_valid_output",
                        step.step_id,
                        existing_output,
                    )
                    continue
                was_approved_before_generation = step.step_id in state.approved_steps
                output_path = self._generate_step_output(
                    step,
                    input_file,
                    output_directory,
                    completed_steps,
                    overwrite or step.step_id in state.stale_steps,
                    review_enabled,
                )
                if was_approved_before_generation:
                    self._mark_downstream_stale(state, step)
                    self._save_state_safely(state, state_path)
            except Exception as error:
                message = f"Step {step.step_id} failed: {error}"
                self.logger.error(
                    "step_failure step=%s error=%s",
                    step.step_id,
                    redact_secrets(error),
                )
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
                self.logger.error(
                    "step_failure step=%s error=%s",
                    step.step_id,
                    redact_secrets(error),
                )
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
                self.logger.info("workflow_quit step=%s", step.step_id)
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
            if review_outcome in {
                ReviewDecision.APPROVE,
                ReviewDecision.EDIT,
                ReviewDecision.SKIP,
            }:
                mark_step_approved(state, step.step_id)
            self._save_state_safely(state, state_path)
            print(f"[{step.step_id}] Wrote {output_path}")
            self.logger.info(
                "step_complete step=%s output=%s", step.step_id, output_path
            )

        if result.failed_step_id is None and not result.quit_requested:
            try:
                index_result = self.index_writer.write_indexes(
                    output_directory,
                    self.workflow_steps,
                    run_metadata={
                        "generated_at": "not recorded",
                        "completed_steps": len(result.completed_step_ids),
                        "codex_task_export_dir": self._codex_task_dir().as_posix(),
                        "workflow_state": state.to_dict(),
                    },
                )
            except Exception as error:
                message = f"Index generation failed: {error}"
                self.logger.error("step_failure step=index error=%s", redact_secrets(error))
                self._fail(result, "index", message)

            result.index_paths = {
                "README": index_result.readme_path,
                "PROJECT_CONTEXT": index_result.project_context_path,
                "PROMPT_INDEX": index_result.prompt_index_path,
                "ASSUMPTIONS": index_result.assumptions_path,
                "OPEN_QUESTIONS": index_result.open_questions_path,
                "WORKFLOW_STATE": index_result.workflow_state_path,
                "GENERATION_SUMMARY": index_result.generation_summary_path,
                "VALIDATION_REPORT": index_result.validation_report_path,
                "CHANGELOG": index_result.changelog_path,
            }
            result.index_warnings = list(index_result.warnings)
            for output_key, output_path in result.index_paths.items():
                if output_path is not None:
                    state.output_files[output_key] = str(output_path)
            state.workflow_status = "stale" if state.stale_steps else "completed"
            state.current_step = None
            state.next_step = state.stale_steps[0] if state.stale_steps else None
            self._save_state_safely(state, state_path)
            for warning in result.index_warnings:
                print(f"[index] Warning: {warning}")
                self.logger.warning("index_warning message=%s", warning)
            print(f"[index] Wrote {index_result.readme_path}")
            print(f"[index] Wrote {index_result.project_context_path}")
            self.logger.info(
                "workflow_complete completed_steps=%s status=%s",
                len(result.completed_step_ids),
                state.workflow_status,
            )

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
        backend_name = getattr(self.generation_backend, "backend_name", None)
        validation = self._run_output_validator(
            content,
            step.required_sections,
            expected_h1=step.name if backend_name in {"manual_chatgpt", "codex"} else None,
            backend_name=backend_name,
        )
        if not validation["is_valid"]:
            self.logger.error(
                "validation_failure step=%s errors=%s",
                step.step_id,
                "; ".join(validation["errors"]),
            )
            raise WorkflowRunError(
                f"Invalid generated Markdown for {step.step_id}: "
                + "; ".join(validation["errors"])
            )
        self._handle_validation_warnings(step, validation["warnings"])

    def _generate_step_output(
        self,
        step: WorkflowStep,
        input_file: Path,
        output_directory: Path,
        completed_steps: list[WorkflowStep],
        overwrite: bool,
        review_enabled: bool,
    ) -> Path:
        context = self.context_builder(
            step, input_file, output_directory, completed_steps
        )
        context = dict(context)
        context.update(
            {
                "OUTPUT_ROOT": str(output_directory),
                "EXPECTED_H1": step.name,
                "REQUIRED_SECTIONS": list(step.required_sections),
                "PENDING_PROMPT_PATH": str(
                    output_directory / self._manual_prompt_dir() / f"{step.step_id}.prompt.md"
                ),
                "MANUAL_RESPONSE_PATH": str(
                    output_directory / self._manual_response_dir() / f"{step.step_id}.response.md"
                ),
                "CODEX_TASK_PATH": str(
                    output_directory / self._codex_task_dir() / step.step_id
                ),
                "TARGET_OUTPUT_PATH": str(output_directory / step.output_path),
                "OVERWRITE": overwrite,
            }
        )
        prompt = self.prompt_loader(step.prompt_template_path, context)
        generated_markdown = self.generation_backend.generate(
            step=step,
            prompt=prompt,
            context=context,
        )
        self._validate_generated_markdown(step, generated_markdown)
        generation_metadata = self._generation_metadata_for_step(
            step, output_directory, context, review_enabled
        )
        self._generation_metadata_by_step[step.step_id] = generation_metadata
        output_path = self.markdown_writer(
            output_directory,
            step.output_path,
            generated_markdown,
            overwrite,
            frontmatter=self._frontmatter_for_step(
                step, review_enabled, generation_metadata
            ),
        )
        return output_path

    def _manual_prompt_dir(self) -> Path:
        return Path(
            self._backend_config("manual_chatgpt")
            .get("prompt_export_dir", "99-meta/pending-prompts")
        )

    def _manual_response_dir(self) -> Path:
        return Path(
            self._backend_config("manual_chatgpt")
            .get("response_import_dir", "99-meta/manual-responses")
        )

    def _codex_task_dir(self) -> Path:
        return Path(
            self._backend_config("codex")
            .get("task_export_dir", "99-meta/codex-tasks")
        )

    def _backend_config(self, backend_name: str) -> dict[str, Any]:
        backends_config = self.config.get("backends") or {}
        if not isinstance(backends_config, dict):
            return {}
        backend_config = backends_config.get(backend_name) or {}
        if not isinstance(backend_config, dict):
            return {}
        return backend_config

    def _frontmatter_for_step(
        self,
        step: WorkflowStep,
        review_enabled: bool,
        generation_metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        metadata = generation_metadata or {}
        frontmatter = {
            "title": step.name,
            "document_id": step.step_id,
            "document_type": "workflow_output",
            "workflow_step": step.step_id,
            "status": "generated",
            "review_status": "pending" if review_enabled else "not_required",
            "depends_on": list(step.depends_on_step_ids),
            "blocks": list(step.blocks_step_ids),
            "tags": [
                "ai-agile/workflow-output",
                f"ai-agile/{step.step_id}",
            ],
        }
        for key in (
            "generation_backend",
            "generation_mode",
            "model",
            "prompt_file",
            "response_file",
            "task_folder",
            "target_output",
            "generated_at",
        ):
            if key in metadata:
                frontmatter[key] = metadata[key]
        return frontmatter

    def _generation_metadata_for_step(
        self,
        step: WorkflowStep,
        output_directory: Path,
        context: dict[str, Any],
        review_enabled: bool,
    ) -> dict[str, Any]:
        backend_name = getattr(self.generation_backend, "backend_name", None)
        generation_mode = getattr(self.generation_backend, "generation_mode", None)
        if backend_name is None:
            backend_name = self.generation_backend.__class__.__name__
        if generation_mode is None:
            generation_mode = "automated"
        generated_at = (
            "not recorded"
            if backend_name == "mock"
            else datetime.now(timezone.utc).isoformat()
        )

        metadata: dict[str, Any] = {
            "step_id": step.step_id,
            "status": "generated",
            "review_status": "pending" if review_enabled else "not_required",
            "generation_backend": backend_name,
            "generation_mode": generation_mode,
            "target_output": _relative_path(output_directory / step.output_path, output_directory),
            "generated_at": generated_at,
        }

        model = getattr(self.generation_backend, "model", None)
        if model:
            metadata["model"] = str(model)

        if backend_name == "manual_chatgpt":
            metadata["prompt_file"] = _relative_path(
                Path(context["PENDING_PROMPT_PATH"]), output_directory
            )
            metadata["response_file"] = _relative_path(
                Path(context["MANUAL_RESPONSE_PATH"]), output_directory
            )
        elif backend_name == "codex":
            metadata["task_folder"] = _relative_path(
                Path(context["CODEX_TASK_PATH"]), output_directory
            )
        return metadata

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
                    review_enabled=review_enabled,
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
            mark_step_skipped(
                state,
                step.step_id,
                output_path,
                next_step=next_step_id,
                generation_metadata=self._generation_metadata_by_step.get(step.step_id),
            )
        else:
            mark_step_completed(
                state,
                step.step_id,
                output_path,
                next_step=next_step_id,
                generation_metadata=self._generation_metadata_by_step.get(step.step_id),
            )

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
        backend_name = getattr(self.generation_backend, "backend_name", None)
        validation = self._run_output_validator(
            content,
            step.required_sections,
            expected_h1=step.name if backend_name in {"manual_chatgpt", "codex"} else None,
            backend_name=backend_name,
        )
        if not validation["is_valid"]:
            return False
        return not (self.fail_on_warnings and validation["warnings"])

    def _run_output_validator(
        self,
        content: str,
        required_sections: list[str] | None,
        expected_h1: str | None = None,
        backend_name: str | None = None,
    ) -> dict[str, Any]:
        try:
            return self.output_validator(
                content,
                required_sections,
                expected_h1=expected_h1,
                backend_name=backend_name,
            )
        except TypeError:
            return self.output_validator(content, required_sections)

    def _handle_validation_warnings(
        self, step: WorkflowStep, warnings: list[str]
    ) -> None:
        if not warnings:
            return
        if self.fail_on_warnings:
            self.logger.error(
                "validation_failure step=%s warnings=%s",
                step.step_id,
                "; ".join(warnings),
            )
            raise WorkflowRunError(
                f"Validation warnings for {step.step_id}: " + "; ".join(warnings)
            )
        for warning in warnings:
            print(f"[{step.step_id}] Warning: {warning}")
            self.logger.warning("validation_warning step=%s message=%s", step.step_id, warning)

    def _fail(
        self, result: WorkflowRunResult, step_id: str, message: str
    ) -> None:
        result.failed_step_id = step_id
        result.errors.append(message)
        safe_message = redact_secrets(message)
        self.logger.error("workflow_failure step=%s error=%s", step_id, safe_message)
        raise WorkflowRunError(safe_message)


class _LLMClientBackendAdapter:
    """Adapter for legacy clients that expose generate(prompt)."""

    def __init__(self, llm_client: Any) -> None:
        self.llm_client = llm_client

    def generate(self, step: Any, prompt: str, context: dict[str, Any]) -> str:
        return self.llm_client.generate(prompt)


def _relative_path(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()
