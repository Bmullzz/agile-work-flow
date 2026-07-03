# Review Mode

Review mode adds a human approval gate after each generated document.

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --review
```

## Decisions

After each output, the terminal prompts:

```text
[a] Approve and continue
[e] Edit manually, then continue
[r] Regenerate this document
[s] Skip this step
[q] Quit workflow
```

## Approve

Validates the generated Markdown and marks the step approved in `.workflow-state.json`.

## Edit

Edit the generated file in your editor, then return to the terminal and press Enter. The file is reread and revalidated before approval.

If the step was previously approved, editing it marks downstream dependent documents stale.

## Regenerate

Runs the same step again. If the step was previously approved, downstream dependent documents are marked stale.

Use `--overwrite` when rerunning review workflows where outputs already exist.

## Skip

Allowed only when a valid output file already exists. Skip validates the existing file before approving it.

## Quit

Saves partial state, sets workflow status to paused, and exits safely. Continue later with:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --resume --review
```

## Review and Dependencies

In review mode, downstream steps require approved dependencies. This prevents later prompts from using unreviewed or stale planning documents.

## Stale Recovery

When stale steps exist, rerun from the first stale step:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --resume --review --overwrite
```

You can also start explicitly:

```bash
python run_workflow.py --input input/app-idea.md --output output/my-project --from-step 03-system-architecture --review --overwrite
```
