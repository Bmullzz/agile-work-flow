"""Common generation backend interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class GenerationBackendError(RuntimeError):
    """Raised when a generation backend cannot produce usable Markdown."""


class GenerationBackend(ABC):
    """Backend interface used by the workflow runner."""

    @abstractmethod
    def generate(
        self,
        step: Any,
        prompt: str,
        context: dict[str, Any],
    ) -> str:
        """Generate Markdown for a workflow step."""
