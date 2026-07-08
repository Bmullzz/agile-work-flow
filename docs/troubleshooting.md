# Troubleshooting

## Missing API Key

Symptom:

```text
OPENAI_API_KEY is not configured
```

Fixes:

- Add `OPENAI_API_KEY` to `.env` or the shell environment.
- Use an API-free backend:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --backend manual-chatgpt
python run_workflow.py --input input/app-idea.md --output output/my-project --backend codex
python run_workflow.py --input input/app-idea.md --output output/mock-project --backend mock
```

Manual ChatGPT, Codex task export, and mock mode do not require `OPENAI_API_KEY`.

## Unsupported Backend

Symptom:

```text
Unknown generation backend
```

Fix: use one of:

```text
openai-api
manual-chatgpt
codex
mock
```

## Disabled Backend

Symptom:

```text
Generation backend '<name>' is disabled in config.yaml.
```

Fix: set the backend to `enabled: true` in `config.yaml`, or choose a different backend with `--backend`.

## Invalid Input File

Symptoms:

- `Input file was not found`
- `Input file must be a Markdown file`
- `Input file is too vague`

Fix: provide a `.md` file with a clear app description. `# App Idea` is recommended.

## Missing Prompt Template

Symptom: the workflow fails before the backend call for a step.

Fix: verify the step template exists under `prompts/` and is not empty. The registry in `scripts/workflow_steps.py` defines expected template paths.

## Failed OpenAI API Call

Symptoms:

- provider timeout
- rate limit
- empty response
- OpenAI generation failed

Fixes:

- Check `OPENAI_API_KEY`.
- Check `llm.model`, `timeout_seconds`, retry settings, and `backends.openai_api.max_output_tokens` in `config.yaml`.
- Retry later if the provider failure is temporary.
- Use `--backend mock` to verify local workflow mechanics.

## Missing Manual ChatGPT Response File

Symptom:

```text
Manual ChatGPT response file was not found
```

Fix: save the ChatGPT response exactly where the terminal tells you:

```text
output/my-project/99-meta/manual-responses/<step-id>.response.md
```

Then press Enter in the terminal.

## Stale Manual ChatGPT Response

Symptom:

```text
Manual ChatGPT response file is older than the exported prompt
```

Fix: replace the response file after the new prompt is exported. This prevents a rerun from silently importing old output.

## Validation Failure

Symptoms:

- `must start with a Markdown heading`
- `must start with expected H1`
- `missing required sections`
- `contains chat preamble`
- `must not wrap the entire document in a fenced code block`
- `contains unresolved placeholder markers`

Fixes:

- Edit the generated or imported Markdown so it starts with the expected `# Heading`.
- Add the missing required sections.
- Remove phrases such as `Sure, here is...` or `Here's the Markdown...`.
- Remove outer ```markdown fences around the whole document.
- Replace unresolved placeholders such as `{{APP_IDEA}}`.
- Rerun the failed step with `--step <step-id> --overwrite`.

## Codex Target Path Mismatch

Symptom:

```text
Codex task target failed validation
```

Fix: ensure `target-file.txt` points to the official workflow output path for the current step and stays inside the selected output directory.

## Existing Files Are Skipped

By default, valid existing outputs are protected and skipped. Use `--overwrite` to intentionally regenerate.

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --from-step 07-technical-stories --overwrite
```

## Resume Starts In The Wrong Place

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
