# Codex Mode

Codex mode exports each workflow step as a structured task packet. It is API-free for task export and does not require `OPENAI_API_KEY`.

This mode is export-only. The workflow creates task folders for manual Codex use; it does not invoke the Codex CLI automatically.

## Run Command

```bash
python run_workflow.py \
  --input input/app-idea.md \
  --output output/my-project \
  --backend codex
```

## Generated Task Folders

Task packets are written under:

```text
output/my-project/99-meta/codex-tasks/<step-id>/
```

Example:

```text
output/my-project/99-meta/codex-tasks/03-system-architecture/
  prompt.md
  context.md
  expected-output.md
  target-file.txt
  instructions.md
```

## Task Files

- `prompt.md`: the full rendered workflow prompt
- `context.md`: app idea, dependency outputs, and workflow context
- `expected-output.md`: required sections and validation rules
- `target-file.txt`: the official output file Codex should create or update
- `instructions.md`: human-readable instructions for running the task in Codex

The backend validates that `target-file.txt` points to the expected workflow output path and stays inside the output folder.

## How To Use A Task Packet

1. Open the task folder in Codex.
2. Ask Codex to read `prompt.md`, `context.md`, and `expected-output.md`.
3. Ask Codex to create or update the file listed in `target-file.txt`.
4. Ensure the final output is Markdown only.
5. Run or resume the workflow as needed so the normal validation and state tracking can continue.

## Validation Expectations

Codex-created workflow documents should:

- start with the expected H1 heading
- include required sections from `expected-output.md`
- avoid chat preambles
- avoid wrapping the whole document in a fenced code block
- avoid unresolved placeholders such as `{{APP_IDEA}}`
- write only the target file listed in `target-file.txt`

## Configuration

```yaml
generation:
  backend: codex

backends:
  codex:
    enabled: true
    task_export_dir: 99-meta/codex-tasks
    mode: export_only
```

The CLI can override the config:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --backend codex
```

Use a custom task directory with:

```yaml
backends:
  codex:
    enabled: true
    task_export_dir: 99-meta/codex-tasks
    mode: export_only
```

Generated README links use the configured task directory.
