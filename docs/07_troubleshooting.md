# Troubleshooting

## Missing API Key

Symptom:

```text
OPENAI_API_KEY is not configured
```

Fix:

```bash
cp .env.example .env
```

Add your key to `.env`, or run with `--mock-llm`.

## Invalid Input File

Symptoms:

- `Input file was not found`
- `Input file must be a Markdown file`
- `Input file is too vague`

Fix: provide a `.md` file with a clear app description. `# App Idea` is recommended.

## Missing Prompt Template

Symptom: the workflow fails before the LLM call for a step.

Fix: verify the step template exists under `prompts/` and is not empty. The registry in `scripts/workflow_steps.py` defines the expected template paths.

## Failed LLM Call

Symptoms:

- Provider timeout
- Rate limit
- Empty response
- OpenAI generation failed

Fixes:

- Check `OPENAI_API_KEY`.
- Check `llm.model`, `timeout_seconds`, and retry settings in `config.yaml`.
- Retry later if the provider failure is temporary.
- Use `--mock-llm` to verify local workflow mechanics.

## Validation Failure

Symptoms:

- `Generated Markdown must start with a heading`
- `Generated Markdown is missing required sections`

Fixes:

- Review the relevant prompt template and required sections in `scripts/workflow_steps.py`.
- Regenerate the step with `--step <step-id> --overwrite`.
- In review mode, manually edit the document and continue only after validation passes.

## Existing Files Are Skipped

By default, valid existing outputs are protected and skipped. Use `--overwrite` to intentionally regenerate.

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --from-step 07-technical-stories --overwrite
```

## Resume Starts in the Wrong Place

Check state:

```text
output/my-project/.workflow-state.json
output/my-project/workflow-state.md
```

If stale steps are present, resume starts from the earliest stale or incomplete step. If state is invalid JSON, fix or remove the state file and rerun with explicit `--from-step`.

## Stale Documents

Stale documents are caused by editing or regenerating approved upstream outputs. They are tracked in `.workflow-state.json`.

Fix:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --resume --overwrite
```

## Logs

Workflow logs are written to:

```text
output/my-project/logs/workflow.log
```

Logs include workflow start, step start, completion, skip, failure, validation failure, retry, and completion events. Secrets are redacted.
