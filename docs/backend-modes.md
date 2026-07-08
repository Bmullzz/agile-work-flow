# Backend Modes

AI Agile Workflow can generate documents through four backends. Select a default in `config.yaml` with `generation.backend`, or override it per run with `--backend`.

Backend aliases accepted by the CLI:

- `openai-api` maps to `openai_api`
- `manual-chatgpt` maps to `manual_chatgpt`
- `codex` maps to `codex`
- `mock` maps to `mock`

## Mode 1: OpenAI API

OpenAI API mode is fully automated. It renders each workflow prompt, sends it to the OpenAI API, validates the Markdown response, writes the official output file, and continues to the next step.

Use this mode for unattended full workflow runs.

Requirements:

- `OPENAI_API_KEY` in the environment or `.env`
- `llm.model`, retry, and timeout settings in `config.yaml`
- `backends.openai_api.enabled: true`

```bash
python run_workflow.py \
  --input input/app-idea.md \
  --output output/my-project \
  --backend openai-api
```

## Mode 2: Manual ChatGPT

Manual ChatGPT mode does not use the API and does not require `OPENAI_API_KEY`. For each step, it exports a prompt file, waits while you paste that prompt into ChatGPT, then imports the Markdown response from the expected response file.

Use this mode when you want to use a ChatGPT subscription manually while keeping the local workflow state, validation, and output package.

```bash
python run_workflow.py \
  --input input/app-idea.md \
  --output output/my-project \
  --backend manual-chatgpt \
  --review
```

Prompt files are written to:

```text
output/my-project/99-meta/pending-prompts/<step-id>.prompt.md
```

Response files are read from:

```text
output/my-project/99-meta/manual-responses/<step-id>.response.md
```

## Mode 3: Codex Task Export

Codex mode does not require `OPENAI_API_KEY` for task export. It creates a self-contained task packet for each workflow step so a user can run that task manually in Codex.

Use this mode when you want Codex-ready task folders instead of direct API generation.

```bash
python run_workflow.py \
  --input input/app-idea.md \
  --output output/my-project \
  --backend codex
```

Task packets are written to:

```text
output/my-project/99-meta/codex-tasks/<step-id>/
```

Each task folder contains `prompt.md`, `context.md`, `expected-output.md`, `target-file.txt`, and `instructions.md`.

This backend is export-only. It does not automate the Codex CLI.

## Mode 4: Mock

Mock mode is for tests, local debugging, and smoke checks. It makes no external AI call and produces deterministic fake Markdown.

```bash
python run_workflow.py \
  --input input/app-idea.md \
  --output output/mock-project \
  --backend mock
```

`--mock-llm` remains available as a shortcut for `--backend mock`.

## CLI Override

The CLI flag wins over `config.yaml`:

```bash
python run_workflow.py --input input/app-idea.md --output output/test --backend mock
```

If `generation.backend` is `openai_api` but the command passes `--backend manual-chatgpt`, the run uses Manual ChatGPT mode.

## Review, Resume, And Rerun

Review mode works with all backends. With Manual ChatGPT mode, `--review` is useful because it lets you inspect or edit each imported response before downstream steps consume it.

Resume and rerun behavior is the same for all backends:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --resume
python run_workflow.py --input input/app-idea.md --output output/my-project --from-step 07-technical-stories --overwrite
python run_workflow.py --input input/app-idea.md --output output/my-project --step 03-system-architecture --overwrite
```

Manual response files are checked for freshness. If a response file is older than the newly exported prompt, the run fails instead of silently reusing stale content.
