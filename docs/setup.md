# Setup

## Requirements

- Python 3.10 or newer
- Local shell access
- Network access only when installing dependencies or using the real OpenAI client

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Dependencies:

- `PyYAML` for `config.yaml`
- `openai` for real LLM generation
- `python-dotenv` for optional local `.env` loading

## Environment

Create a local `.env` file when you plan to use the real LLM client:

```bash
cp .env.example .env
```

Then edit `.env`:

```text
OPENAI_API_KEY=your_api_key_here
```

Do not put API keys or tokens in `config.yaml`. The config loader rejects secret-like keys.

## Verify Install

Run the test suite:

```bash
python -m unittest
```

Run the workflow without API calls:

```bash
python run_workflow.py --input input/app-idea.md --output output/mock-project --mock-llm
```

The mock run should create Markdown output files, indexes, workflow state, and `logs/workflow.log`.
