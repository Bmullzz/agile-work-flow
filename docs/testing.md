# Testing

## Run All Tests

```bash
python -m unittest
```

The suite uses `FakeLLMClient` and does not require API keys or network access.

## Focused Test Commands

```bash
python -m unittest tests.test_cli
python -m unittest tests.test_config_loader
python -m unittest tests.test_workflow_runner
python -m unittest tests.test_end_to_end_mock
python -m unittest tests.test_review_gate
```

## Mock Smoke Run

```bash
python run_workflow.py --input input/app-idea.md --output output/mock-project --mock-llm --overwrite
```

Expected results:

- All 16 workflow documents are created.
- Generated Markdown starts with a heading.
- `README.md` and `project-context.md` are created.
- `.workflow-state.json` is written.
- `logs/workflow.log` is written.

## Real LLM Smoke Run

```bash
OPENAI_API_KEY=your_api_key_here python run_workflow.py --input input/app-idea.md --output output/real-project --overwrite
```

Use a small test idea first. Real runs make API calls and may incur provider cost.

## What Tests Cover

- CLI parsing
- Config loading and secret rejection
- File utilities
- Input validation
- Prompt loading and rendering
- Workflow step registry
- Markdown writing and path safety
- Context building
- Fake and mocked real LLM clients
- Runner orchestration
- Review gate behavior
- State persistence and stale tracking
- Index and metadata generation
- Logging and error handling
