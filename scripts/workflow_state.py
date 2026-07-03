"""Local JSON persistence for workflow execution state."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.models import WorkflowState


STATE_FILE_NAME = ".workflow-state.json"


class WorkflowStateError(RuntimeError):
    """Raised when workflow state cannot be loaded or saved."""


def create_initial_state(
    project_name: str,
    input_file: str | Path,
    output_folder: str | Path,
    next_step: str | None = None,
) -> WorkflowState:
    return WorkflowState(
        project_name=project_name,
        input_file=str(input_file),
        output_folder=str(output_folder),
        workflow_status="not_started",
        next_step=next_step,
    )


def load_state(path: str | Path) -> WorkflowState:
    state_path = Path(path)
    try:
        raw_state = state_path.read_text(encoding="utf-8")
        data = json.loads(raw_state)
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as error:
        raise WorkflowStateError(f"Invalid workflow state JSON: {state_path}") from error
    except OSError as error:
        raise WorkflowStateError(f"Could not read workflow state: {state_path}") from error

    if not isinstance(data, dict):
        raise WorkflowStateError(f"Workflow state must be a JSON object: {state_path}")

    try:
        return WorkflowState.from_dict(data)
    except KeyError as error:
        raise WorkflowStateError(
            f"Workflow state is missing required field: {error.args[0]}"
        ) from error


def save_state(state: WorkflowState, path: str | Path) -> Path:
    state_path = Path(path)
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(state.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        raise WorkflowStateError(f"Could not write workflow state: {state_path}") from error
    return state_path


def mark_step_started(
    state: WorkflowState, step_id: str, next_step: str | None = None
) -> WorkflowState:
    state.workflow_status = "running"
    state.current_step = step_id
    state.next_step = next_step
    state.failed_step = None
    return state


def mark_step_completed(
    state: WorkflowState,
    step_id: str,
    output_file: str | Path,
    next_step: str | None = None,
) -> WorkflowState:
    if step_id not in state.completed_steps:
        state.completed_steps.append(step_id)
    state.output_files[step_id] = str(output_file)
    state.current_step = None
    state.next_step = next_step
    state.failed_step = None
    state.workflow_status = "completed" if next_step is None else "running"
    return state


def mark_step_skipped(
    state: WorkflowState,
    step_id: str,
    output_file: str | Path,
    next_step: str | None = None,
) -> WorkflowState:
    state.output_files[step_id] = str(output_file)
    state.current_step = None
    state.next_step = next_step
    state.failed_step = None
    state.workflow_status = "completed" if next_step is None else "running"
    return state


def mark_step_failed(state: WorkflowState, step_id: str) -> WorkflowState:
    state.workflow_status = "failed"
    state.failed_step = step_id
    state.current_step = step_id
    return state


def mark_workflow_quit(state: WorkflowState, step_id: str) -> WorkflowState:
    state.workflow_status = "paused"
    state.current_step = step_id
    state.next_step = step_id
    state.pending_review_step = step_id
    return state


def mark_step_approved(state: WorkflowState, step_id: str) -> WorkflowState:
    if step_id not in state.approved_steps:
        state.approved_steps.append(step_id)
    if state.pending_review_step == step_id:
        state.pending_review_step = None
    return state


def state_file_path(output_root: str | Path) -> Path:
    return Path(output_root) / STATE_FILE_NAME
