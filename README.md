# AI Agile Workflow

AI Agile Workflow is a local Python CLI that turns a Markdown app idea into a structured agile planning package. It runs a fixed sequence of prompt templates, sends each rendered prompt to either a fake offline LLM or the OpenAI API, validates the Markdown response, writes outputs, and records workflow state locally.

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
python run_workflow.py --input input/app-idea.md --output output/mock-project --mock-llm
```

Run with the real OpenAI-backed client:

```bash
OPENAI_API_KEY=your_api_key_here python run_workflow.py --input input/app-idea.md --output output/my-project
```

You can also put `OPENAI_API_KEY` in a local `.env` file. Secrets are not read from `config.yaml`.

## CLI Usage

Required flags:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project
```

Common options:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --mock-llm
python run_workflow.py --input input/app-idea.md --output output/my-project --review
python run_workflow.py --input input/app-idea.md --output output/my-project --resume
python run_workflow.py --input input/app-idea.md --output output/my-project --from-step 07-technical-stories --overwrite
python run_workflow.py --input input/app-idea.md --output output/my-project --step 03-system-architecture --overwrite
```

Use `--mock-llm` for local testing without network access or API keys. Omit it for real OpenAI generation.

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
```

Generated documents include YAML frontmatter for Markdown tools such as Obsidian while remaining readable in VS Code, Cursor, GitHub, and plain Markdown editors.

## Documentation

- [Setup](docs/setup.md)
- [Usage](docs/usage.md)
- [Configuration](docs/configuration.md)
- [Workflow](docs/workflow.md)
- [Review Mode](docs/review-mode.md)
- [Testing](docs/testing.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Developer Guide](docs/developer-guide.md)

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

- The real provider implementation currently targets OpenAI.
- Prompt rendering uses simple `{{PLACEHOLDER}}` replacement, not Jinja.
- Review mode is terminal-based.
- State is local JSON, not collaborative or remotely synchronized.
- Generated content quality depends on the prompt templates and selected model.

## Extension Points

Future work can add provider adapters behind `generate(prompt: str) -> str`, richer validators, alternate prompt packs, metadata exporters, or a UI without changing the core runner contract.
