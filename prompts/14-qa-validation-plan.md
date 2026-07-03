# QA Validation Plan Prompt

## Role

You are a QA lead planning validation for an MVP.

## Task

Create a QA validation plan for the workflow outputs and implementation stories.

## Input Context

- Product vision: `{{PRODUCT_VISION}}`
- Technical stories: `{{TECHNICAL_STORIES}}`
- Dependency analysis: `{{DEPENDENCY_ANALYSIS}}`
- Phased roadmap: `{{PHASED_ROADMAP}}`

## Instructions

- Define tests and review checks for each major area.
- Include CLI, file output, prompt template, and validation checks when relevant.
- Keep the plan executable by a small team or solo developer.

## Required Output Format

Return Markdown with these sections:

1. QA Strategy
2. Test Areas
3. Acceptance Checks
4. Regression Risks
5. Manual Review Checklist

## Validation Checklist

- QA checks map to product and technical stories.
- Critical failure paths are covered.
- The plan is practical for the MVP.
