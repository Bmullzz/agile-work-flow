"""Compatibility exports for generation backends.

New code should import backend classes from scripts.backends. These names remain
for existing callers and tests that still use the older LLM client terminology.
"""

from __future__ import annotations

from typing import Any, Protocol

from scripts.backends.base import GenerationBackendError
from scripts.backends.mock_backend import MockGenerationBackend
from scripts.backends.openai_api_backend import OpenAIAPIBackend


class LLMClient(Protocol):
    def generate(self, prompt: str) -> str:
        """Generate Markdown text for a rendered prompt."""


class LLMClientError(GenerationBackendError):
    """Backward-compatible LLM client error."""


class FakeLLMClient:
    """Backward-compatible wrapper around MockGenerationBackend."""

    def __init__(self) -> None:
        self.backend = MockGenerationBackend()

    def generate(self, prompt: str) -> str:
        return self.backend.generate(step=None, prompt=prompt, context={}).replace(
            "MockGenerationBackend", "FakeLLMClient"
        )


class OpenAILLMClient(OpenAIAPIBackend):
    """Backward-compatible wrapper around OpenAIAPIBackend."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        try:
            super().__init__(*args, **kwargs)
        except GenerationBackendError as error:
            raise LLMClientError(str(error)) from error

    def generate(self, prompt: str, *args: Any, **kwargs: Any) -> str:
        if args or kwargs:
            return super().generate(prompt=prompt, *args, **kwargs)
        try:
            return super().generate(step=None, prompt=prompt, context={})
        except GenerationBackendError as error:
            raise LLMClientError(str(error)) from error
