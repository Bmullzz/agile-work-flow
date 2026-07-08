# Configuration

The current configuration reference is maintained at [configuration.md](configuration.md).

Key points:

- `generation.backend` selects the default backend.
- `--backend` overrides config for one run.
- `OPENAI_API_KEY` is required only for `openai_api`.
- Manual ChatGPT, Codex task export, and mock mode are API-free.
- Backend-specific settings live under `backends`.

Minimal backend config:

```yaml
generation:
  backend: openai_api

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

OpenAI model, retry, timeout, and temperature settings remain under `llm`.
