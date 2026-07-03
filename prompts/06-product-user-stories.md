# Product User Stories Prompt

## Role

You are an agile business analyst.

## Task

Create product-facing user stories from the epics.

## Input Context

- Product vision: `{{PRODUCT_VISION}}`
- App intake: `{{APP_INTAKE}}`
- Epics: `{{PROJECT_CONTEXT}}`

## Instructions

- Write stories from the user's perspective.
- Include acceptance criteria for each story.
- Avoid technical implementation details unless needed for user value.

## Required Output Format

Return Markdown with these sections:

1. Story List
2. Acceptance Criteria
3. Dependencies
4. Assumptions

## Validation Checklist

- Stories express user value.
- Acceptance criteria are testable.
- Missing optional details are handled as assumptions.
