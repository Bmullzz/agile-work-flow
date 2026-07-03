"""Interactive review gate for generated workflow documents."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Callable

from scripts.models import WorkflowStep
from scripts.validators import validate_markdown_file


class ReviewDecision(Enum):
    APPROVE = "approve"
    EDIT = "edit"
    REGENERATE = "regenerate"
    SKIP = "skip"
    QUIT = "quit"


class ReviewGateError(RuntimeError):
    """Raised when a review decision cannot be completed safely."""


class ReviewGate:
    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        validator: Callable[[Path], dict] = validate_markdown_file,
    ) -> None:
        self.input_func = input_func
        self.validator = validator

    def review(self, step: WorkflowStep, output_path: str | Path) -> ReviewDecision:
        path = Path(output_path)
        print(f"\nReview generated document for {step.step_id}: {path}")

        while True:
            command = self.input_func(
                "[a] Approve and continue\n"
                "[e] Edit manually, then continue\n"
                "[r] Regenerate this document\n"
                "[s] Skip this step\n"
                "[q] Quit workflow\n"
                "Choice: "
            ).strip().lower()

            if command == "a":
                self._validate_output(path)
                return ReviewDecision.APPROVE
            if command == "e":
                self.input_func("Edit the file, then press Enter to continue: ")
                self._validate_output(path)
                return ReviewDecision.EDIT
            if command == "r":
                return ReviewDecision.REGENERATE
            if command == "s":
                self._validate_output(path)
                return ReviewDecision.SKIP
            if command == "q":
                return ReviewDecision.QUIT

            print("Invalid review command. Choose a, e, r, s, or q.")

    def _validate_output(self, path: Path) -> None:
        validation = self.validator(path)
        if not validation["is_valid"]:
            raise ReviewGateError(
                "Reviewed document is invalid: " + "; ".join(validation["errors"])
            )
