"""Generate navigation files for a completed workflow output package."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import re
from typing import Any, Iterable

from scripts.markdown_writer import write_markdown
from scripts.models import WorkflowStep


@dataclass
class IndexWriteResult:
    readme_path: Path
    project_context_path: Path
    prompt_index_path: Path | None = None
    prompt_by_story_paths: list[Path] = field(default_factory=list)
    prompt_by_phase_paths: list[Path] = field(default_factory=list)
    assumptions_path: Path | None = None
    open_questions_path: Path | None = None
    workflow_state_path: Path | None = None
    generation_summary_path: Path | None = None
    validation_report_path: Path | None = None
    changelog_path: Path | None = None
    warnings: list[str] = field(default_factory=list)


@dataclass
class _PromptPackageResult:
    index_path: Path
    by_story_paths: list[Path] = field(default_factory=list)
    by_phase_paths: list[Path] = field(default_factory=list)


@dataclass
class _PromptSection:
    title: str
    content: str


class IndexWriteError(RuntimeError):
    """Raised when output index files cannot be written."""


class IndexWriter:
    def write_indexes(
        self,
        output_root: str | Path,
        workflow_steps: Iterable[WorkflowStep],
        run_metadata: dict[str, Any] | None = None,
    ) -> IndexWriteResult:
        output_directory = Path(output_root)
        steps = list(workflow_steps)
        metadata = run_metadata or {}
        warnings: list[str] = []

        existing_steps = []
        for step in steps:
            output_path = output_directory / step.output_path
            if output_path.exists():
                existing_steps.append(step)
            else:
                warnings.append(f"Missing optional output skipped: {step.output_path}")

        try:
            prompt_package = self._write_prompt_package(output_directory, steps, warnings)
            readme_path = write_markdown(
                output_directory,
                "README.md",
                self._render_readme(existing_steps, metadata, warnings),
                overwrite=True,
                frontmatter=_frontmatter(
                    "AI Agile Workflow Output",
                    "README",
                    "index",
                    tags=["ai-agile/index"],
                ),
            )
            project_context_path = write_markdown(
                output_directory,
                "project-context.md",
                self._render_project_context(existing_steps, metadata, warnings),
                overwrite=True,
                frontmatter=_frontmatter(
                    "Project Context",
                    "project-context",
                    "context",
                    tags=["ai-agile/context", "ai-agile/index"],
                ),
            )
            assumptions_path = write_markdown(
                output_directory,
                "assumptions.md",
                self._render_assumptions(existing_steps),
                overwrite=True,
                frontmatter=_frontmatter(
                    "Assumptions",
                    "assumptions",
                    "metadata",
                    tags=["ai-agile/meta", "ai-agile/assumptions"],
                ),
            )
            open_questions_path = write_markdown(
                output_directory,
                "open-questions.md",
                self._render_open_questions(existing_steps),
                overwrite=True,
                frontmatter=_frontmatter(
                    "Open Questions",
                    "open-questions",
                    "metadata",
                    tags=["ai-agile/meta", "ai-agile/questions"],
                ),
            )
            workflow_state_path = write_markdown(
                output_directory,
                "workflow-state.md",
                self._render_workflow_state(metadata),
                overwrite=True,
                frontmatter=_frontmatter(
                    "Workflow State",
                    "workflow-state",
                    "metadata",
                    tags=["ai-agile/meta", "ai-agile/state"],
                ),
            )
            generation_summary_path = write_markdown(
                output_directory,
                "99-meta/generation-summary.md",
                self._render_generation_summary(existing_steps, metadata, warnings),
                overwrite=True,
                frontmatter=_frontmatter(
                    "Generation Summary",
                    "99-meta/generation-summary",
                    "metadata",
                    tags=["ai-agile/meta", "ai-agile/summary"],
                ),
            )
            validation_report_path = write_markdown(
                output_directory,
                "99-meta/validation-report.md",
                self._render_validation_report(steps, existing_steps, warnings),
                overwrite=True,
                frontmatter=_frontmatter(
                    "Validation Report",
                    "99-meta/validation-report",
                    "metadata",
                    tags=["ai-agile/meta", "ai-agile/validation"],
                ),
            )
            changelog_path = write_markdown(
                output_directory,
                "99-meta/changelog.md",
                self._render_changelog(metadata),
                overwrite=True,
                frontmatter=_frontmatter(
                    "Changelog",
                    "99-meta/changelog",
                    "metadata",
                    tags=["ai-agile/meta", "ai-agile/changelog"],
                ),
            )
        except Exception as error:
            raise IndexWriteError(f"Failed to write output indexes: {error}") from error

        return IndexWriteResult(
            readme_path=readme_path,
            project_context_path=project_context_path,
            prompt_index_path=prompt_package.index_path,
            prompt_by_story_paths=prompt_package.by_story_paths,
            prompt_by_phase_paths=prompt_package.by_phase_paths,
            assumptions_path=assumptions_path,
            open_questions_path=open_questions_path,
            workflow_state_path=workflow_state_path,
            generation_summary_path=generation_summary_path,
            validation_report_path=validation_report_path,
            changelog_path=changelog_path,
            warnings=warnings,
        )

    def _render_readme(
        self,
        workflow_steps: list[WorkflowStep],
        metadata: dict[str, Any],
        warnings: list[str],
    ) -> str:
        lines = [
            "# AI Agile Workflow Output",
            "",
            "This folder contains generated planning documents for the workflow run.",
            "",
        ]
        lines.extend(_render_metadata(metadata))
        lines.extend(
            [
                "## Recommended Implementation Path",
                "",
                "1. Review the product and technical foundation documents.",
                "2. Read the phased roadmap and dependency analysis.",
                "3. Use the coding-agent prompts to implement stories in order.",
                "4. Validate work against the QA validation plan.",
                "",
            ]
        )

        coding_agent_step = _find_step(workflow_steps, "12-coding-agent-prompts")
        if coding_agent_step is not None:
            lines.extend(
                [
                    "## Coding-Agent Prompts",
                    "",
                    "- [Prompt Index](06-agent-prompts/prompt-index.md)",
                    "- [Project Setup Prompt](06-agent-prompts/13-project-setup-prompt.md) - run this first",
                    f"- [Coding-Agent Prompts]({_markdown_link(coding_agent_step.output_path)})",
                    "- [Codex Task Packets](99-meta/codex-tasks/)",
                    "",
                ]
            )

        lines.extend(["## Generated Documents", ""])
        for step in workflow_steps:
            lines.append(f"- [{step.name}]({_markdown_link(step.output_path)})")
        lines.append("")

        lines.extend(
            [
                "## Vault Metadata",
                "",
                "- [Assumptions](assumptions.md) ([[assumptions|Obsidian]])",
                "- [Open Questions](open-questions.md) ([[open-questions|Obsidian]])",
                "- [Workflow State](workflow-state.md) ([[workflow-state|Obsidian]])",
                "- [Generation Summary](99-meta/generation-summary.md)",
                "- [Validation Report](99-meta/validation-report.md)",
                "- [Changelog](99-meta/changelog.md)",
                "",
            ]
        )

        if warnings:
            lines.extend(["## Warnings", ""])
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    def _write_prompt_package(
        self,
        output_directory: Path,
        workflow_steps: list[WorkflowStep],
        warnings: list[str],
    ) -> "_PromptPackageResult":
        agent_prompt_directory = output_directory / "06-agent-prompts"
        by_story_directory = agent_prompt_directory / "by-story"
        by_phase_directory = agent_prompt_directory / "by-phase"
        by_story_directory.mkdir(parents=True, exist_ok=True)
        by_phase_directory.mkdir(parents=True, exist_ok=True)

        setup_step = _find_step(workflow_steps, "13-project-setup-prompt")
        combined_step = _find_step(workflow_steps, "12-coding-agent-prompts")
        optimized_stories_step = _find_step(
            workflow_steps, "11-coding-agent-optimized-stories"
        )
        technical_stories_step = _find_step(workflow_steps, "07-technical-stories")
        dependency_analysis_step = _find_step(workflow_steps, "09-dependency-analysis")

        combined_prompt_path = (
            output_directory / combined_step.output_path if combined_step else None
        )
        combined_prompt_content = ""
        if combined_prompt_path is not None and combined_prompt_path.exists():
            combined_prompt_content = combined_prompt_path.read_text(encoding="utf-8")
        elif combined_step is not None:
            warnings.append(
                "Missing combined coding-agent prompt file; prompt splitting skipped."
            )

        by_story_paths = self._write_story_prompt_files(
            output_directory,
            combined_prompt_content,
            combined_step,
        )
        prompt_entries = self._prompt_entries_from_story_paths(
            output_directory,
            by_story_paths,
            technical_stories_step,
            dependency_analysis_step,
        )
        by_phase_paths = self._write_phase_prompt_files(output_directory, prompt_entries)

        index_path = write_markdown(
            output_directory,
            "06-agent-prompts/prompt-index.md",
            self._render_prompt_index(
                setup_step=setup_step,
                combined_step=combined_step,
                optimized_stories_step=optimized_stories_step,
                technical_stories_step=technical_stories_step,
                dependency_analysis_step=dependency_analysis_step,
                prompt_entries=prompt_entries,
            ),
            overwrite=True,
            frontmatter=_frontmatter(
                "Coding-Agent Prompt Index",
                "06-agent-prompts/prompt-index",
                "agent_prompt_index",
                workflow_step="12-coding-agent-prompts",
                depends_on=[
                    step.step_id
                    for step in (
                        setup_step,
                        combined_step,
                        optimized_stories_step,
                        technical_stories_step,
                        dependency_analysis_step,
                    )
                    if step is not None
                ],
                tags=["ai-agile/agent-prompts", "ai-agile/index"],
            ),
        )
        return _PromptPackageResult(
            index_path=index_path,
            by_story_paths=by_story_paths,
            by_phase_paths=by_phase_paths,
        )

    def _write_story_prompt_files(
        self,
        output_directory: Path,
        combined_prompt_content: str,
        combined_step: WorkflowStep | None,
    ) -> list[Path]:
        if not combined_prompt_content.strip() or combined_step is None:
            return []
        sections = _split_prompt_sections(combined_prompt_content)
        paths = []
        for index, section in enumerate(sections, start=1):
            story_id = _story_id_from_title(section.title, index)
            prompt_path = write_markdown(
                output_directory,
                f"06-agent-prompts/by-story/{story_id}.md",
                section.content,
                overwrite=True,
                frontmatter=_frontmatter(
                    section.title,
                    f"06-agent-prompts/by-story/{story_id}",
                    "agent_prompt",
                    workflow_step=combined_step.step_id,
                    depends_on=list(combined_step.depends_on_step_ids),
                    tags=["ai-agile/agent-prompts", "ai-agile/by-story"],
                ),
            )
            paths.append(prompt_path)
        return paths

    def _prompt_entries_from_story_paths(
        self,
        output_directory: Path,
        by_story_paths: list[Path],
        technical_stories_step: WorkflowStep | None,
        dependency_analysis_step: WorkflowStep | None,
    ) -> list[dict[str, str]]:
        entries = []
        for index, path in enumerate(by_story_paths, start=1):
            story_id = path.stem
            phase = _phase_from_story_id(story_id, index)
            dependencies = []
            if dependency_analysis_step is not None:
                dependencies.append(_source_link(dependency_analysis_step.output_path))
            source = (
                _source_link(technical_stories_step.output_path)
                if technical_stories_step is not None
                else "technical stories"
            )
            entries.append(
                {
                    "order": str(index + 1),
                    "story_id": story_id,
                    "phase": phase,
                    "dependencies": ", ".join(dependencies) or "none",
                    "source": source,
                    "path": _markdown_link(
                        path.relative_to(output_directory / "06-agent-prompts")
                    ),
                }
            )
        return entries

    def _write_phase_prompt_files(
        self, output_directory: Path, prompt_entries: list[dict[str, str]]
    ) -> list[Path]:
        entries_by_phase: dict[str, list[dict[str, str]]] = {}
        for entry in prompt_entries:
            entries_by_phase.setdefault(entry["phase"], []).append(entry)

        phase_paths = []
        for phase in sorted(entries_by_phase):
            phase_paths.append(
                write_markdown(
                    output_directory,
                    f"06-agent-prompts/by-phase/{phase}.md",
                    self._render_phase_prompt_file(phase, entries_by_phase[phase]),
                    overwrite=True,
                    frontmatter=_frontmatter(
                        f"Coding-Agent Prompts {phase}",
                        f"06-agent-prompts/by-phase/{phase}",
                        "agent_prompt_phase",
                        workflow_step="12-coding-agent-prompts",
                        tags=["ai-agile/agent-prompts", "ai-agile/by-phase"],
                    ),
                )
            )
        return phase_paths

    def _render_phase_prompt_file(
        self, phase: str, prompt_entries: list[dict[str, str]]
    ) -> str:
        lines = [
            f"# Coding-Agent Prompts {phase}",
            "",
            "Run these prompts in order for this phase.",
            "",
        ]
        for entry in prompt_entries:
            lines.append(f"- [{entry['story_id']}](../{entry['path']})")
        lines.append("")
        return "\n".join(lines)

    def _render_prompt_index(
        self,
        setup_step: WorkflowStep | None,
        combined_step: WorkflowStep | None,
        optimized_stories_step: WorkflowStep | None,
        technical_stories_step: WorkflowStep | None,
        dependency_analysis_step: WorkflowStep | None,
        prompt_entries: list[dict[str, str]],
    ) -> str:
        lines = [
            "# Coding-Agent Prompt Index",
            "",
            "Use this index to run implementation prompts in dependency order.",
            "",
            "## Execution Order",
            "",
        ]
        if setup_step is not None:
            lines.append(
                f"1. [Project Setup Prompt]({_agent_prompt_link(setup_step.output_path)}) - run this first"
            )
        else:
            lines.append("1. Project setup prompt missing - create project scaffolding first.")
        if prompt_entries:
            for entry in prompt_entries:
                lines.append(
                    f"{entry['order']}. [{entry['story_id']}]({entry['path']}) - {entry['phase']}"
                )
        elif combined_step is not None:
            lines.append(
                f"2. [Combined Coding-Agent Prompts]({_agent_prompt_link(combined_step.output_path)})"
            )
        else:
            lines.append("2. Combined coding-agent prompt file missing.")

        lines.extend(["", "## Prompt Map", ""])
        if setup_step is not None:
            lines.extend(
                [
                    "| Order | Prompt | Phase | Dependencies | Source Technical Story |",
                    "| --- | --- | --- | --- | --- |",
                    f"| 1 | [project-setup]({_agent_prompt_link(setup_step.output_path)}) | setup | none | project setup |",
                ]
            )
        else:
            lines.extend(
                [
                    "| Order | Prompt | Phase | Dependencies | Source Technical Story |",
                    "| --- | --- | --- | --- | --- |",
                    "| 1 | project-setup missing | setup | none | project setup |",
                ]
            )
        for entry in prompt_entries:
            lines.append(
                "| {order} | [{story_id}]({path}) | {phase} | {dependencies} | {source} |".format(
                    **entry
                )
            )
        if not prompt_entries and combined_step is not None:
            source = (
                _source_link(technical_stories_step.output_path)
                if technical_stories_step is not None
                else "technical stories"
            )
            dependencies = (
                _source_link(dependency_analysis_step.output_path)
                if dependency_analysis_step is not None
                else "none"
            )
            lines.append(
                f"| 2 | [combined-prompts]({_agent_prompt_link(combined_step.output_path)}) | implementation | {dependencies} | {source} |"
            )

        lines.extend(["", "## Source Documents", ""])
        for label, step in (
            ("Optimized Stories", optimized_stories_step),
            ("Technical Stories", technical_stories_step),
            ("Dependency Analysis", dependency_analysis_step),
            ("Combined Prompts", combined_step),
        ):
            if step is not None:
                lines.append(f"- [{label}]({_source_link(step.output_path)})")
        lines.extend(["", "## Folders", ""])
        lines.append("- [By Story](by-story/)")
        lines.append("- [By Phase](by-phase/)")
        lines.append("")
        return "\n".join(lines)

    def _render_project_context(
        self,
        workflow_steps: list[WorkflowStep],
        metadata: dict[str, Any],
        warnings: list[str],
    ) -> str:
        lines = [
            "# Project Context",
            "",
            "Generated context index for this AI Agile Workflow output package.",
            "",
        ]
        lines.extend(_render_metadata(metadata))
        lines.extend(["## Document Map", ""])
        for step in workflow_steps:
            lines.append(f"- {step.step_id}: [{step.name}]({_markdown_link(step.output_path)})")
        lines.append("")

        lines.extend(
            [
                "## Implementation Guidance",
                "",
                "Start with the roadmap, then follow dependency order through the coding-agent prompts.",
                "",
                "## Vault Links",
                "",
                "- [[assumptions|Assumptions]]",
                "- [[open-questions|Open Questions]]",
                "- [[workflow-state|Workflow State]]",
                "",
            ]
        )

        if warnings:
            lines.extend(["## Warnings", ""])
            for warning in warnings:
                lines.append(f"- {warning}")
            lines.append("")

        return "\n".join(lines)

    def _render_assumptions(self, workflow_steps: list[WorkflowStep]) -> str:
        lines = [
            "# Assumptions",
            "",
            "Assumptions identified during generation or review should be collected here.",
            "",
            "## Sources",
            "",
        ]
        for step in workflow_steps:
            lines.append(f"- [{step.name}]({_markdown_link(step.output_path)})")
        lines.extend(["", "## Assumptions Log", "", "- No assumptions have been recorded yet.", ""])
        return "\n".join(lines)

    def _render_open_questions(self, workflow_steps: list[WorkflowStep]) -> str:
        lines = [
            "# Open Questions",
            "",
            "Track unresolved product, technical, and delivery questions here.",
            "",
            "## Related Documents",
            "",
        ]
        for step in workflow_steps:
            lines.append(f"- [{step.name}]({_markdown_link(step.output_path)})")
        lines.extend(["", "## Questions", "", "- No open questions have been recorded yet.", ""])
        return "\n".join(lines)

    def _render_workflow_state(self, metadata: dict[str, Any]) -> str:
        state = metadata.get("workflow_state") or {}
        lines = ["# Workflow State", ""]
        if isinstance(state, dict) and state:
            lines.extend(
                [
                    f"- Project: {state.get('project_name', 'unknown')}",
                    f"- Status: {state.get('workflow_status', 'unknown')}",
                    f"- Current step: {state.get('current_step') or 'none'}",
                    f"- Next step: {state.get('next_step') or 'none'}",
                    f"- Failed step: {state.get('failed_step') or 'none'}",
                    "",
                    "## Completed Steps",
                    "",
                ]
            )
            completed_steps = state.get("completed_steps") or []
            if completed_steps:
                for step_id in completed_steps:
                    lines.append(f"- {step_id}")
            else:
                lines.append("- None")
            lines.extend(["", "## Stale Steps", ""])
            stale_steps = state.get("stale_steps") or []
            if stale_steps:
                for step_id in stale_steps:
                    lines.append(f"- {step_id}")
            else:
                lines.append("- None")
        else:
            lines.append("Workflow state was not available when this file was generated.")
        lines.append("")
        return "\n".join(lines)

    def _render_generation_summary(
        self,
        workflow_steps: list[WorkflowStep],
        metadata: dict[str, Any],
        warnings: list[str],
    ) -> str:
        lines = [
            "# Generation Summary",
            "",
            f"- Generated documents: {len(workflow_steps)}",
            f"- Warnings: {len(warnings)}",
            "",
        ]
        lines.extend(_render_metadata(metadata))
        lines.extend(["## Documents", ""])
        for step in workflow_steps:
            lines.append(f"- {step.step_id}: [{step.name}](../{_markdown_link(step.output_path)})")
        lines.append("")
        return "\n".join(lines)

    def _render_validation_report(
        self,
        workflow_steps: list[WorkflowStep],
        existing_steps: list[WorkflowStep],
        warnings: list[str],
    ) -> str:
        existing_step_ids = {step.step_id for step in existing_steps}
        lines = ["# Validation Report", "", "## Output Presence", ""]
        for step in workflow_steps:
            status = "present" if step.step_id in existing_step_ids else "missing"
            lines.append(f"- {step.step_id}: {status}")
        lines.extend(["", "## Required Sections", ""])
        for step in workflow_steps:
            required_sections = ", ".join(step.required_sections) or "none"
            lines.append(f"- {step.step_id}: {required_sections}")
        if warnings:
            lines.extend(["", "## Warnings", ""])
            for warning in warnings:
                lines.append(f"- {warning}")
        lines.append("")
        return "\n".join(lines)

    def _render_changelog(self, metadata: dict[str, Any]) -> str:
        generated_at = metadata.get("generated_at") or datetime.now(timezone.utc).isoformat()
        lines = [
            "# Changelog",
            "",
            "## Initial Generation",
            "",
            f"- Generated workflow output package at {generated_at}.",
            "- Created navigation and Obsidian-friendly metadata files.",
            "",
        ]
        return "\n".join(lines)


def _render_metadata(metadata: dict[str, Any]) -> list[str]:
    generated_at = metadata.get("generated_at") or datetime.now(timezone.utc).isoformat()
    lines = [
        "## Run Metadata",
        "",
        f"- Generated at: {generated_at}",
    ]
    for key in sorted(metadata):
        if key in {"generated_at", "workflow_state"}:
            continue
        lines.append(f"- {key.replace('_', ' ').title()}: {metadata[key]}")
    lines.extend(["", ""])
    return lines


def _find_step(workflow_steps: list[WorkflowStep], step_id: str) -> WorkflowStep | None:
    for step in workflow_steps:
        if step.step_id == step_id:
            return step
    return None


def _markdown_link(path: Path) -> str:
    return path.as_posix()


def _agent_prompt_link(path: Path) -> str:
    path = Path(path)
    parts = path.parts
    if parts and parts[0] == "06-agent-prompts":
        return Path(*parts[1:]).as_posix()
    return path.as_posix()


def _source_link(path: Path) -> str:
    return "../" + Path(path).as_posix()


def _split_prompt_sections(content: str) -> list[_PromptSection]:
    markdown = _strip_yaml_frontmatter(content).strip()
    matches = list(re.finditer(r"^(#{2,3})\s+(.+?)\s*$", markdown, flags=re.MULTILINE))
    if not matches:
        return []

    sections: list[_PromptSection] = []
    prompt_heading_matches = [
        match for match in matches if _is_prompt_section_heading(match.group(2))
    ]
    for match in prompt_heading_matches:
        start = match.start()
        end = _prompt_section_end(markdown, matches, match)
        section_content = markdown[start:end].strip()
        if section_content:
            sections.append(
                _PromptSection(
                    title=match.group(2).strip().rstrip("#").strip(),
                    content=section_content,
                )
            )
    return sections


def _prompt_section_end(
    markdown: str, heading_matches: list[re.Match[str]], current_match: re.Match[str]
) -> int:
    current_level = len(current_match.group(1))
    for candidate in heading_matches:
        if candidate.start() <= current_match.start():
            continue
        candidate_level = len(candidate.group(1))
        if _is_prompt_section_heading(candidate.group(2)) or candidate_level <= current_level:
            return candidate.start()
    return len(markdown)


def _is_prompt_section_heading(title: str) -> bool:
    return bool(_story_identifier_match(title))


def _strip_yaml_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    match = re.match(r"^---\s*\n.*?\n---\s*\n?", content, flags=re.DOTALL)
    if not match:
        return content
    return content[match.end() :]


def _story_id_from_title(title: str, index: int) -> str:
    identifier_match = _story_identifier_match(title)
    if identifier_match:
        return _slugify(identifier_match.group(1))
    return f"{index:03d}-{_slugify(title)}"


def _story_identifier_match(title: str) -> re.Match[str] | None:
    return re.search(
        r"\b((?:story|us|ts|task|prompt)[-_ ]?\d+[a-z0-9-]*)\b",
        title,
        flags=re.IGNORECASE,
    )


def _phase_from_story_id(story_id: str, index: int) -> str:
    phase_match = re.search(r"phase[-_ ]?(\d+)", story_id, flags=re.IGNORECASE)
    if phase_match:
        return f"phase-{int(phase_match.group(1)):02d}"
    phase_number = ((index - 1) // 5) + 1
    return f"phase-{phase_number:02d}"


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "prompt"


def _frontmatter(
    title: str,
    document_id: str,
    document_type: str,
    workflow_step: str = "index",
    status: str = "generated",
    review_status: str = "not_required",
    depends_on: list[str] | None = None,
    blocks: list[str] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "title": title,
        "document_id": document_id,
        "document_type": document_type,
        "workflow_step": workflow_step,
        "status": status,
        "review_status": review_status,
        "depends_on": depends_on or [],
        "blocks": blocks or [],
        "tags": tags or ["ai-agile"],
    }
