# Workflow

The workflow has 16 canonical steps. Each step has one prompt template, one output path, dependency metadata, and required Markdown sections.

## Step Order

1. `00-app-intake`
2. `01-product-vision`
3. `02-tech-stack`
4. `03-system-architecture`
5. `04-user-journeys`
6. `05-epics`
7. `06-product-user-stories`
8. `07-technical-stories`
9. `08-stories-by-application-layer`
10. `09-dependency-analysis`
11. `10-phased-roadmap`
12. `11-coding-agent-optimized-stories`
13. `12-coding-agent-prompts`
14. `13-project-setup-prompt`
15. `14-qa-validation-plan`
16. `15-documentation-plan`

The canonical registry is `scripts/workflow_steps.py`.

## Runtime Flow

For each step, the runner:

1. Checks completed, valid dependencies.
2. Builds context from the app idea and declared dependency outputs.
3. Renders the Markdown prompt template.
4. Calls the injected LLM client.
5. Validates generated Markdown and required sections.
6. Writes the output file with frontmatter.
7. Updates `.workflow-state.json`.
8. Runs review mode if enabled.

After successful completion, `IndexWriter` generates navigation and metadata files.

## Context Rules

Every prompt receives `APP_IDEA`. Dependency outputs are loaded only when declared by the step. Known dependency outputs are mapped to stable placeholders such as:

- `APP_INTAKE`
- `PRODUCT_VISION`
- `TECH_STACK`
- `SYSTEM_ARCHITECTURE`
- `TECHNICAL_STORIES`
- `DEPENDENCY_ANALYSIS`
- `PHASED_ROADMAP`

If `project-context.md` exists, it is included as `PROJECT_CONTEXT`.

## Generated Output Structure

```text
00-intake/00-app-intake.md
01-product/01-product-vision.md
02-technical/02-tech-stack.md
02-technical/03-system-architecture.md
03-discovery/04-user-journeys.md
03-discovery/05-epics.md
04-stories/06-product-user-stories.md
04-stories/07-technical-stories.md
04-stories/08-stories-by-application-layer.md
05-planning/09-dependency-analysis.md
05-planning/10-phased-roadmap.md
06-agent-prompts/11-coding-agent-optimized-stories.md
06-agent-prompts/12-coding-agent-prompts.md
06-agent-prompts/13-project-setup-prompt.md
07-quality/14-qa-validation-plan.md
08-documentation/15-documentation-plan.md
```

Additional generated files:

```text
README.md
project-context.md
assumptions.md
open-questions.md
workflow-state.md
06-agent-prompts/prompt-index.md
06-agent-prompts/by-story/
06-agent-prompts/by-phase/
99-meta/generation-summary.md
99-meta/validation-report.md
99-meta/changelog.md
99-meta/state/workflow-state.json
```

## Stale Documents

When an approved upstream document is edited or regenerated, downstream dependent steps are marked stale in state. Stale outputs are not treated as approved context in review mode and resume starts from the earliest stale step.
