# AI Agile Workflow

AI Agile Workflow is a local Python CLI that turns a Markdown app idea into a structured agile planning package. It runs a fixed sequence of prompt templates, sends each rendered prompt to a configurable generation backend, validates the Markdown response, writes outputs, and records workflow state locally.

The MVP is intentionally script-based. It does not include a web UI, database, RAG system, vector store, or multi-agent orchestration.

## Quick Start

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -m unittest
```

Run the full workflow offline with deterministic mock output:

```bash
python run_workflow.py --input input/app-idea.md --output output/mock-project --backend mock
```

Run with the real OpenAI-backed client:

```bash
OPENAI_API_KEY=your_api_key_here python run_workflow.py --input input/app-idea.md --output output/my-project --backend openai-api
```

You can also put `OPENAI_API_KEY` in a local `.env` file. Secrets are not read from `config.yaml`.

Run with manual ChatGPT prompt export and response import:

```bash
python run_workflow.py --input input/app-idea.md --output output/manual-project --backend manual-chatgpt --review
```

This mode does not require `OPENAI_API_KEY`.

Run with Codex task packet export:

```bash
python run_workflow.py --input input/app-idea.md --output output/codex-project --backend codex
```

This mode exports self-contained task packets and does not require `OPENAI_API_KEY`.

## CLI Usage

Required flags:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project
```

Common options:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --mock-llm
python run_workflow.py --input input/app-idea.md --output output/my-project --backend openai-api
python run_workflow.py --input input/app-idea.md --output output/my-project --backend manual-chatgpt
python run_workflow.py --input input/app-idea.md --output output/my-project --backend codex
python run_workflow.py --input input/app-idea.md --output output/my-project --backend mock
python run_workflow.py --input input/app-idea.md --output output/my-project --review
python run_workflow.py --input input/app-idea.md --output output/my-project --resume
python run_workflow.py --input input/app-idea.md --output output/my-project --from-step 07-technical-stories --overwrite
python run_workflow.py --input input/app-idea.md --output output/my-project --step 03-system-architecture --overwrite
```

Use `--backend` to override `generation.backend` from `config.yaml`. Backend aliases are normalized internally, so `openai-api` maps to `openai_api` and `manual-chatgpt` maps to `manual_chatgpt`. `--mock-llm` remains a shortcut for `--backend mock`.

Backend configuration:

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

## Manual ChatGPT Mode

Manual ChatGPT mode is a subscription-friendly backend that avoids API calls. Configure:

```yaml
generation:
  backend: manual_chatgpt
```

For each workflow step, the backend exports the rendered prompt to:

```text
output/my-project/99-meta/pending-prompts/<step-id>.prompt.md
```

The terminal then tells you where to save the ChatGPT response:

```text
output/my-project/99-meta/manual-responses/<step-id>.response.md
```

Paste the prompt into ChatGPT, save the Markdown response at that path, then press Enter in the terminal. The backend imports the response and validates it before the normal workflow output writer continues.

Manual responses must start with the expected H1, include required sections, avoid chat preambles such as `Sure, here is...`, avoid unresolved `{{PLACEHOLDER}}` markers, and avoid wrapping the whole document in a fenced code block.

## Codex Export Mode

Codex export mode creates one task packet per workflow step under:

```text
output/my-project/99-meta/codex-tasks/<step-id>/
```

Each packet contains `prompt.md`, `context.md`, `expected-output.md`, `target-file.txt`, and `instructions.md`. Open the task folder in Codex, ask it to read those files, and have it create or update the file listed in `target-file.txt`.

This first version is export-only. It does not run the Codex CLI automatically.

## Input Format

The only required user input is a meaningful Markdown app idea file. `# App Idea` is recommended, but optional when the description is clear.

```markdown
# App Idea

I want to build a local AI workflow tool that generates planning documents from an app idea.
```

Very vague inputs such as `App.` or `Something with AI.` fail validation before the workflow starts.

## Generated Output

Each workflow run writes Markdown under the selected output folder:

```text
output/my-project/
  README.md
  project-context.md
  assumptions.md
  open-questions.md
  workflow-state.md
  .workflow-state.json
  logs/workflow.log
  00-intake/
  01-product/
  02-technical/
  03-discovery/
  04-stories/
  05-planning/
  06-agent-prompts/
  07-quality/
  08-documentation/
  99-meta/
    codex-tasks/
    pending-prompts/
    manual-responses/
```

Generated documents include YAML frontmatter for Markdown tools such as Obsidian while remaining readable in VS Code, Cursor, GitHub, and plain Markdown editors.

## Documentation

- [Setup](docs/01_setup.md)
- [Usage](docs/02_usage.md)
- [Backend Modes](docs/03_backend-modes.md)
- [Manual ChatGPT Mode](docs/04_manual-chatgpt-mode.md)
- [Codex Mode](docs/05_codex-mode.md)
- [Configuration](docs/06_configuration.md)
- [Workflow](docs/07_workflow.md)
- [Review Mode](docs/08_review-mode.md)
- [Testing](docs/09_testing.md)
- [Troubleshooting](docs/10_troubleshooting.md)
- [Developer Guide](docs/11_developer-guide.md)

## Repository Structure

```text
run_workflow.py       # CLI entry point
config.yaml           # Non-secret runtime settings
.env.example          # Environment variable template
input/app-idea.md     # Example app idea
prompts/              # Editable Markdown prompt templates
scripts/              # Workflow implementation modules
tests/                # Unit and end-to-end mock tests
output/               # Generated artifacts
docs/                 # User and developer documentation
```

## Known Limitations

- API-backed generation currently targets OpenAI.
- Manual ChatGPT mode is semi-manual and does not automate or scrape the ChatGPT UI.
- Prompt rendering uses simple `{{PLACEHOLDER}}` replacement, not Jinja.
- Review mode is terminal-based.
- State is local JSON, not collaborative or remotely synchronized.
- Generated content quality depends on the prompt templates and selected model.

## Extension Points

Future work can add provider adapters behind the `GenerationBackend` interface, richer validators, alternate prompt packs, metadata exporters, or a UI without changing the core runner contract.
