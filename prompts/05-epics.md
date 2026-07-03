# Epics Prompt

## Role

You are an agile product owner.

## Task

Create MVP epics from the product vision and user journeys.

## Input Context

- Product vision: `{{PRODUCT_VISION}}`
- User journeys: `{{PROJECT_CONTEXT}}`
- System architecture: `{{SYSTEM_ARCHITECTURE}}`

## Instructions

- Group related capabilities into implementation-sized epics.
- Keep epics outcome-oriented.
- Include acceptance signals for each epic.

## Required Output Format

Return Markdown with these sections:

1. Epic Summary
2. Epics
3. Acceptance Signals
4. Out of Scope

## Validation Checklist

- Epics cover the MVP journeys.
- Epics are not individual tasks.
- Scope remains realistic for an MVP.
