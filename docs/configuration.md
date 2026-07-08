# Configuration

Runtime settings live in `config.yaml`. Secrets live in environment variables or `.env`.

## Required Top-Level Sections

The config loader requires:

- `llm`
- `workflow`
- `output`
- `prompts`

The backend sections are optional in older configs but are used for backend selection and API-free modes.

## Backend Selection

Default backend:

```yaml
generation:
  backend: openai_api
```

Supported backend names:

- `openai_api`
- `manual_chatgpt`
- `codex`
- `mock`

CLI aliases:

```bash
--backend openai-api
--backend manual-chatgpt
--backend codex
--backend mock
```

The CLI flag overrides `generation.backend`.

## Backend Config

```yaml
backends:
  openai_api:
    enabled: true
    max_output_tokens: 4000

  manual_chatgpt:
    enabled: true
    prompt_export_dir: 99-meta/pending-prompts
    response_import_dir: 99-meta/manual-responses

  codex:
    enabled: true
    task_export_dir: 99-meta/codex-tasks
    mode: export_only

  mock:
    enabled: true
```

If a backend has `enabled: false`, selecting it fails before the workflow starts.

## OpenAI API Settings

```yaml
llm:
  provider: openai
  model: gpt-4.1-mini
  temperature: 0.2
  max_retries: 2
  retry_delay_seconds: 0
  timeout_seconds: 60
```

OpenAI API mode requires `OPENAI_API_KEY` in the environment or `.env`.

`backends.openai_api.max_output_tokens` controls the output token limit passed to the OpenAI request. Model and temperature are read from `llm` unless explicitly supplied by backend-specific OpenAI config.

## Manual ChatGPT Settings

```yaml
generation:
  backend: manual_chatgpt

backends:
  manual_chatgpt:
    enabled: true
    prompt_export_dir: 99-meta/pending-prompts
    response_import_dir: 99-meta/manual-responses
```

This mode does not require `OPENAI_API_KEY`.

## Codex Settings

```yaml
generation:
  backend: codex

backends:
  codex:
    enabled: true
    task_export_dir: 99-meta/codex-tasks
    mode: export_only
```

This mode does not require `OPENAI_API_KEY` for task export.

## Mock Settings

```yaml
generation:
  backend: mock

backends:
  mock:
    enabled: true
```

Mock mode is deterministic and intended for tests and local smoke checks.

## Workflow Settings

```yaml
workflow:
  default_review: false
  resume_enabled: true
  stop_on_failure: true
  fail_on_warnings: false
```

- `default_review`: enables review gates by default
- `resume_enabled`: reserved for resume behavior
- `stop_on_failure`: stops on the first failed step when true
- `fail_on_warnings`: treats validation warnings as blocking

## Output Settings

```yaml
output:
  format: markdown
  create_run_directory: true
  overwrite: false
```

`output.overwrite` is overridden by the CLI `--overwrite` flag.

## Prompt Settings

```yaml
prompts:
  directory: prompts
  extension: .md
```

Prompt templates are Markdown files under `prompts/` and use simple placeholders such as `{{APP_IDEA}}`, `{{PRODUCT_VISION}}`, and `{{TECHNICAL_STORIES}}`.
