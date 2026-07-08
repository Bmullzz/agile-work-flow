"""Codex task export generation backend."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from scripts.backends.base import GenerationBackend, GenerationBackendError
from scripts.codex_task_writer import CodexTaskWriter


class CodexBackend(GenerationBackend):
    """Export each workflow step as a Codex-ready task packet."""

    def __init__(self, writer: CodexTaskWriter | None = None) -> None:
        self.writer = writer or CodexTaskWriter()

    def generate(self, step: Any, prompt: str, context: dict[str, Any]) -> str:
        if prompt is None or not str(prompt).strip():
            raise GenerationBackendError("Codex backend requires a non-empty prompt.")

        output_root = context.get("OUTPUT_ROOT")
        if not output_root:
            raise GenerationBackendError("Codex backend requires OUTPUT_ROOT in context.")

        target_output_path = context.get("TARGET_OUTPUT_PATH")
        if not target_output_path:
            target_output_path = Path(output_root) / getattr(step, "output_path")

        overwrite = bool(context.get("OVERWRITE", False))
        result = self.writer.write_task_packet(
            output_root=output_root,
            step=step,
            prompt=prompt,
            context=context,
            target_output_path=target_output_path,
            overwrite=overwrite,
        )

        return _render_export_marker(step, result.task_directory, target_output_path)


def _render_export_marker(step: Any, task_directory: Path, target_output_path: str | Path) -> str:
    required_sections = list(getattr(step, "required_sections", []) or [])
    rendered_sections: set[str] = set()
    lines = [
        f"# Codex Task Exported: {getattr(step, 'name', 'Workflow Step')}",
        "",
        "## Summary",
        "",
        "A Codex-ready task packet was exported for manual execution.",
        "",
        "## Codex Task Packet",
        "",
        f"- Task folder: `{task_directory}`",
        f"- Target output file: `{target_output_path}`",
        "",
    ]
    rendered_sections.update({"Summary", "Codex Task Packet"})

    for section in required_sections:
        if section in rendered_sections:
            continue
        lines.extend(
            [
                f"## {section}",
                "",
                (
                    "Use the exported Codex task packet to produce this section in "
                    "the target workflow document."
                ),
                "",
            ]
        )
        rendered_sections.add(section)

    return "\n".join(lines)
