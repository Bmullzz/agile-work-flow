# Usage

## Basic Command

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project
```

Required flags:

- `--input`: path to the Markdown app idea file
- `--output`: output folder for generated artifacts

## Mock Mode

Use mock mode for offline development, tests, and smoke checks:

```bash
python run_workflow.py --input input/app-idea.md --output output/mock-project --backend mock
```

`--mock-llm` is still available as a shortcut. Mock mode returns deterministic Markdown and does not require API keys or network access.

## OpenAI API Mode

Set `OPENAI_API_KEY` in the environment or `.env`, then run:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --backend openai-api
```

Model, retry, and timeout settings come from `config.yaml`.

## Manual ChatGPT Mode

Manual ChatGPT mode exports a prompt file, waits for you to paste the prompt into ChatGPT, then imports the Markdown response from the expected response file.

```bash
python run_workflow.py --input input/app-idea.md --output output/manual-project --backend manual-chatgpt --review
```

Prompt exports are written under `99-meta/pending-prompts/`. Manual responses are read from `99-meta/manual-responses/`.

## Codex Task Export Mode

Codex mode exports self-contained task packets and does not run the Codex CLI automatically.

```bash
python run_workflow.py --input input/app-idea.md --output output/codex-project --backend codex
```

Task packets are written under `99-meta/codex-tasks/`.

## Review Mode

```bash
python run_workflow.py --input input/app-idea.md --output output/review-project --review
```

The workflow pauses after each generated document. You can approve, edit, regenerate, skip, or quit.

Use `--no-review` to force automatic mode even if `workflow.default_review` is enabled in config.

## Resume and Rerun

Continue from saved state:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --resume
```

Regenerate one step and all following steps:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --from-step 07-technical-stories --overwrite
```

Run one specific step:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --step 03-system-architecture --overwrite
```

Single-step runs require dependency outputs to exist and be valid.

## Overwrite Behavior

Existing valid outputs are skipped by default. Use `--overwrite` when you intentionally want to regenerate files.

Without `--overwrite`, the writer protects existing files and the runner skips valid outputs when possible.

## Output Navigation

Start with the generated output `README.md`, then use:

- `project-context.md` for a document map
- `06-agent-prompts/prompt-index.md` for implementation prompt order
- `.workflow-state.json` for machine-readable state
- `workflow-state.md` for human-readable state
- `logs/workflow.log` for troubleshooting
