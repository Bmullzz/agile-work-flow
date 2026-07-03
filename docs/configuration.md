# Configuration

Runtime settings live in `config.yaml`. Secrets live in environment variables or `.env`.

## Current Defaults

```yaml
llm:
  provider: openai
  model: gpt-4.1-mini
  temperature: 0.2
  max_retries: 2
  retry_delay_seconds: 0
  timeout_seconds: 60

workflow:
  default_review: false
  resume_enabled: true
  stop_on_failure: true
  fail_on_warnings: false

output:
  format: markdown
  create_run_directory: true
  overwrite: false

prompts:
  directory: prompts
  extension: .md
```

## Required Sections

The config loader requires these top-level sections:

- `llm`
- `workflow`
- `output`
- `prompts`

Missing sections, invalid YAML, or secret-like keys fail early.

## LLM Settings

- `llm.provider`: currently `openai`
- `llm.model`: OpenAI model name
- `llm.temperature`: generation temperature
- `llm.max_retries`: retry count for temporary provider failures
- `llm.retry_delay_seconds`: delay between retries
- `llm.timeout_seconds`: provider request timeout

## Workflow Settings

- `workflow.default_review`: enables review gates by default
- `workflow.resume_enabled`: reserved for resume behavior
- `workflow.stop_on_failure`: stops the run on the first failed step when true
- `workflow.fail_on_warnings`: treats Markdown validation warnings as blocking when true

## Output Settings

- `output.format`: currently Markdown
- `output.create_run_directory`: reserved for run directory behavior
- `output.overwrite`: default overwrite behavior, overridden by `--overwrite`

## Prompt Settings

- `prompts.directory`: prompt template directory
- `prompts.extension`: prompt template extension

Prompt templates are Markdown files under `prompts/` and use simple placeholders such as `{{APP_IDEA}}`, `{{PRODUCT_VISION}}`, and `{{TECHNICAL_STORIES}}`.
