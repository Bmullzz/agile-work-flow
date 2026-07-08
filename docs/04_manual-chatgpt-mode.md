# Manual ChatGPT Mode

Manual ChatGPT mode lets you run the workflow without API billing or API keys. The workflow still renders prompts, tracks state, validates Markdown, writes official outputs, and supports review/resume.

## Run Command

```bash
python run_workflow.py \
  --input input/app-idea.md \
  --output output/my-project \
  --backend manual-chatgpt \
  --review
```

`--review` is recommended so each imported response can be approved or edited before downstream documents use it.

## Step Flow

For each workflow step:

1. The backend writes the rendered prompt to:

```text
output/my-project/99-meta/pending-prompts/<step-id>.prompt.md
```

2. The terminal prints the response path:

```text
output/my-project/99-meta/manual-responses/<step-id>.response.md
```

3. Open the prompt file, paste it into ChatGPT, and save the ChatGPT response as Markdown at the response path.
4. Press Enter in the terminal.
5. The backend imports and validates the response.
6. The workflow writes the official step output, such as:

```text
output/my-project/02-technical/03-system-architecture.md
```

## Validation Rules

Manual responses are rejected when they:

- are missing
- are empty
- do not start with the expected H1 heading
- omit required sections for the workflow step
- include chat preambles such as `Sure, here is...`
- wrap the whole document in a fenced code block
- leak unresolved placeholders such as `{{APP_IDEA}}`, `{{PROJECT_CONTEXT}}`, or `{{TECH_STACK}}`

Example failure:

```text
Manual ChatGPT response failed validation:
- Manual ChatGPT response is missing required sections: Risks
- Manual ChatGPT response contains chat preamble: "Sure, here is..."
Please edit the response file and try again.
```

## Resume And Rerun

Manual response files must be newer than the exported prompt file. This prevents accidental reuse of an old ChatGPT response during `--resume`, `--step`, `--from-step`, or review regeneration.

To rerun from a step:

```bash
python run_workflow.py \
  --input input/app-idea.md \
  --output output/my-project \
  --backend manual-chatgpt \
  --from-step 03-system-architecture \
  --overwrite \
  --review
```

When the prompt is re-exported, replace the matching response file with a fresh ChatGPT answer before pressing Enter.

## Configuration

```yaml
generation:
  backend: manual_chatgpt

backends:
  manual_chatgpt:
    enabled: true
    prompt_export_dir: 99-meta/pending-prompts
    response_import_dir: 99-meta/manual-responses
```

The CLI can override the config:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --backend manual-chatgpt
```

No `OPENAI_API_KEY` is required.
