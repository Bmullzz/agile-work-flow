"""OpenAI API generation backend."""

from __future__ import annotations

import os
import time
from typing import Any, Callable

from scripts.backends.base import GenerationBackend, GenerationBackendError
from scripts.logger import get_workflow_logger, redact_secrets


class OpenAIAPIBackend(GenerationBackend):
    """OpenAI-backed generation backend."""

    def __init__(
        self,
        config: dict[str, Any],
        api_key: str | None = None,
        openai_client: Any | None = None,
        env_loader: Callable[[], Any] | None = None,
        logger: Any | None = None,
    ) -> None:
        self.config = config or {}
        backend_config = _openai_config(self.config)
        self.model = backend_config.get("model", "gpt-4.1-mini")
        self.temperature = backend_config.get("temperature", 0.2)
        self.max_retries = int(backend_config.get("max_retries", 2))
        self.retry_delay_seconds = float(backend_config.get("retry_delay_seconds", 0))
        self.timeout_seconds = float(backend_config.get("timeout_seconds", 60))
        self.logger = logger or get_workflow_logger()

        self._load_environment(env_loader)
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise GenerationBackendError(
                "OPENAI_API_KEY is not configured. Add it to your environment "
                "or local .env file, or run with --mock-llm."
            )

        self.client = openai_client or self._create_openai_client()

    def generate(self, step: Any, prompt: str, context: dict[str, Any]) -> str:
        if prompt is None:
            raise ValueError("Prompt cannot be None.")
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

        last_error: Exception | None = None
        attempts = self.max_retries + 1
        for attempt in range(attempts):
            try:
                response = self.client.responses.create(
                    model=self.model,
                    input=prompt,
                    temperature=self.temperature,
                    timeout=self.timeout_seconds,
                )
                text = _extract_response_text(response)
                if not text.strip():
                    raise GenerationBackendError("OpenAI returned an empty response.")
                return text
            except GenerationBackendError:
                raise
            except Exception as error:
                last_error = error
                if attempt >= self.max_retries or not _is_retryable_error(error):
                    raise GenerationBackendError(
                        f"OpenAI generation failed: {_safe_error_message(error)}"
                    ) from error
                self.logger.warning(
                    "llm_retry attempt=%s max_retries=%s step=%s error=%s",
                    attempt + 1,
                    self.max_retries,
                    getattr(step, "step_id", "unknown"),
                    redact_secrets(_safe_error_message(error)),
                )
                if self.retry_delay_seconds > 0:
                    time.sleep(self.retry_delay_seconds)

        raise GenerationBackendError(
            f"OpenAI generation failed: {_safe_error_message(last_error)}"
        )

    def _load_environment(self, env_loader: Callable[[], Any] | None) -> None:
        if env_loader is not None:
            env_loader()
            return

        try:
            from dotenv import load_dotenv
        except ModuleNotFoundError:
            return

        load_dotenv()

    def _create_openai_client(self):
        try:
            from openai import OpenAI
        except ModuleNotFoundError as error:
            raise GenerationBackendError(
                "OpenAI SDK is not installed. Run `pip install -r requirements.txt`."
            ) from error

        return OpenAI(api_key=self.api_key, timeout=self.timeout_seconds, max_retries=0)


def _openai_config(config: dict[str, Any]) -> dict[str, Any]:
    backends_config = config.get("backends", {})
    openai_api_config = backends_config.get("openai_api", {})
    llm_config = config.get("llm", {})
    merged = dict(llm_config)
    merged.update(openai_api_config)
    return merged


def _extract_response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if output_text is not None:
        return str(output_text)

    if isinstance(response, dict):
        output_text = response.get("output_text")
        if output_text is not None:
            return str(output_text)

    raise GenerationBackendError("OpenAI response did not contain Markdown text.")


def _is_retryable_error(error: Exception) -> bool:
    error_name = error.__class__.__name__.lower()
    return any(
        marker in error_name
        for marker in (
            "timeout",
            "connection",
            "ratelimit",
            "rate_limit",
            "internalserver",
            "server",
            "serviceunavailable",
        )
    )


def _safe_error_message(error: Exception | None) -> str:
    if error is None:
        return "unknown provider error"
    message = str(error) or error.__class__.__name__
    api_key = os.environ.get("OPENAI_API_KEY")
    if api_key:
        message = message.replace(api_key, "[redacted]")
    return message
