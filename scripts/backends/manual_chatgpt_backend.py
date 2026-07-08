"""Manual ChatGPT generation backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from scripts.backends.base import GenerationBackend, GenerationBackendError
from scripts.file_utils import ensure_directory, read_markdown_file, write_text_file
from scripts.validators import validate_markdown_content


class ManualChatGPTBackend(GenerationBackend):
    """Export prompts and import manually pasted ChatGPT responses."""

    backend_name = "manual_chatgpt"
    generation_mode = "manual_import"

    def __init__(
        self,
        input_func: Callable[[str], str] = input,
        prompt_directory: str | Path = "99-meta/pending-prompts",
        response_directory: str | Path = "99-meta/manual-responses",
    ) -> None:
        self.input_func = input_func
        self.prompt_directory = Path(prompt_directory)
        self.response_directory = Path(response_directory)

    def generate(self, step: Any, prompt: str, context: dict[str, Any]) -> str:
        if prompt is None or not prompt.strip():
            raise GenerationBackendError("Manual ChatGPT prompt cannot be empty.")

        output_root = _output_root_from_context(context)
        step_id = getattr(step, "step_id", None)
        if not step_id:
            raise GenerationBackendError("Manual ChatGPT backend requires a workflow step ID.")

        prompt_path = self.prompt_path(output_root, step_id)
        response_path = self.response_path(output_root, step_id)
        ensure_directory(response_path.parent)
        write_text_file(prompt_path, _render_prompt_export(step, prompt), overwrite=True)
        prompt_exported_at = prompt_path.stat().st_mtime

        print()
        print("Prompt exported:")
        print(prompt_path)
        print()
        print("Paste this prompt into ChatGPT.")
        print()
        print("Save the ChatGPT response here:")
        print(response_path)
        print()
        self.input_func("Press Enter when the response file is ready.")

        try:
            _validate_response_is_fresh(response_path, prompt_path, prompt_exported_at)
            response_content = read_markdown_file(response_path)
        except FileNotFoundError as error:
            raise GenerationBackendError(
                f"Manual ChatGPT response file was not found: {response_path}"
            ) from error
        except OSError as error:
            raise GenerationBackendError(
                f"Manual ChatGPT response file could not be read: {response_path}"
            ) from error

        validation = validate_markdown_content(
            response_content,
            required_sections=list(getattr(step, "required_sections", []) or []),
            expected_h1=context.get("EXPECTED_H1"),
            backend_name=self.backend_name,
        )
        if not validation["is_valid"]:
            if any("empty" in error.lower() for error in validation["errors"]):
                raise GenerationBackendError(
                    f"Manual ChatGPT response file is empty: {response_path}"
                )
            raise GenerationBackendError(
                "Manual ChatGPT response failed validation:\n- "
                + "\n- ".join(validation["errors"])
                + f"\nPlease edit the response file and try again: {response_path}"
            )
        return response_content

    def prompt_path(self, output_root: str | Path, step_id: str) -> Path:
        return Path(output_root) / self.prompt_directory / f"{step_id}.prompt.md"

    def response_path(self, output_root: str | Path, step_id: str) -> Path:
        return Path(output_root) / self.response_directory / f"{step_id}.response.md"


def _output_root_from_context(context: dict[str, Any]) -> Path:
    output_root = context.get("OUTPUT_ROOT")
    if output_root is None:
        raise GenerationBackendError(
            "Manual ChatGPT backend requires OUTPUT_ROOT in generation context."
        )
    return Path(output_root)


def _render_prompt_export(step: Any, prompt: str) -> str:
    step_id = getattr(step, "step_id", "unknown-step")
    step_name = getattr(step, "name", "Workflow Step")
    return (
        f"# Manual ChatGPT Prompt: {step_name}\n\n"
        f"- Step ID: {step_id}\n\n"
        "Copy the prompt below into ChatGPT, then save the response to the matching "
        "manual response file.\n\n"
        "## Prompt\n\n"
        f"{prompt.rstrip()}\n"
    )


def _validate_response_is_fresh(
    response_path: Path,
    prompt_path: Path,
    prompt_exported_at: float,
) -> None:
    if not response_path.exists():
        raise FileNotFoundError(response_path)
    response_updated_at = response_path.stat().st_mtime
    if response_updated_at < prompt_exported_at:
        raise GenerationBackendError(
            "Manual ChatGPT response file is older than the exported prompt. "
            f"Replace the response file after exporting the prompt: {response_path} "
            f"(prompt: {prompt_path})"
        )
