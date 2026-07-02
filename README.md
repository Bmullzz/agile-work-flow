# AI Agile Workflow

Local script-based Python CLI MVP for turning an app idea into agile workflow artifacts.

This initial repository intentionally does not include a web UI, database, RAG system, vector store, or multi-agent orchestration.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional environment setup:

```bash
cp .env.example .env
```

## Run

```bash
python run_workflow.py
```

Use a custom config file:

```bash
python run_workflow.py --config config.yaml
```

## Repository Structure

```text
run_workflow.py       # Local CLI entry point
requirements.txt      # Python dependencies
config.yaml           # Local workflow configuration
.env.example          # Environment variable template
input/app-idea.md     # Starting app idea input
output/               # Generated artifacts
prompts/              # Prompt templates for future stories
scripts/              # Supporting Python modules
tests/                # Test package
```
