# Developer Guide

## Architecture

The runner is designed around small, injectable modules:

- `run_workflow.py`: CLI parsing and top-level wiring
- `scripts/workflow_runner.py`: orchestration
- `scripts/workflow_steps.py`: canonical step registry
- `scripts/models.py`: workflow data models
- `scripts/config_loader.py`: non-secret YAML config
- `scripts/context_builder.py`: dependency-based prompt context
- `scripts/prompt_loader.py`: Markdown template loading and placeholder replacement
- `scripts/llm_client.py`: fake and OpenAI-backed clients
- `scripts/markdown_writer.py`: safe Markdown output writer
- `scripts/validators.py`: input and generated Markdown validation
- `scripts/review_gate.py`: interactive approval gate
- `scripts/workflow_state.py`: local JSON state
- `scripts/index_writer.py`: generated README, metadata, and prompt package
- `scripts/logger.py`: console and file logging

## Adding a Workflow Step

1. Add a prompt template in `prompts/`.
2. Add a `WorkflowStep` entry in `scripts/workflow_steps.py`.
3. Define `output_path`, dependencies, and `required_sections`.
4. Add or update tests in `tests/test_workflow_steps.py`.
5. Ensure context placeholders used by the template are supplied by `context_builder.py`.

## Adding an LLM Provider

Implement the same interface:

```python
def generate(prompt: str) -> str:
    ...
```

Keep provider-specific behavior inside the client. The runner should not depend on SDK details.

## Validation Contract

Generated Markdown must:

- Not be empty
- Start with a Markdown heading after optional YAML frontmatter
- Include the step's required sections

Warnings can be made blocking with `workflow.fail_on_warnings: true`.

## State Contract

State is persisted to:

```text
output/<project>/.workflow-state.json
output/<project>/99-meta/state/workflow-state.json
```

The state tracks completed, failed, approved, pending review, current, next, stale, and output file metadata.

## Prompt Package Contract

`IndexWriter` creates:

```text
06-agent-prompts/prompt-index.md
06-agent-prompts/by-story/
06-agent-prompts/by-phase/
```

The splitter only creates individual story prompt files for headings with implementation identifiers such as `TS-001`, `US-002`, `Story 3`, `Task 4`, or `Prompt 5`.

## Handoff Checklist

Before handing changes to another developer or coding agent:

1. Run `python -m unittest`.
2. Run a mock workflow with `--mock-llm --overwrite`.
3. Check generated `README.md`, `project-context.md`, and `prompt-index.md`.
4. Inspect `logs/workflow.log` for unexpected failures.
5. Confirm no secrets are committed.

## Future Extension Points

- Additional LLM provider clients
- Richer Markdown validators
- Configurable workflow registries
- Alternate prompt template packs
- Exporters for other documentation systems
- Non-terminal review UI
- Collaboration-safe state backend
