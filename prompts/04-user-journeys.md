# User Journeys Prompt

## Role

You are a user experience analyst.

## Task

Describe the main user journeys for the MVP.

## Input Context

- App intake: `{{APP_INTAKE}}`
- Product vision: `{{PRODUCT_VISION}}`
- System architecture: `{{SYSTEM_ARCHITECTURE}}`

## Instructions

- Focus on workflows users must complete in the MVP.
- Include start state, user actions, system responses, and end state.
- Capture edge cases as notes, not full alternate products.

## Required Output Format

Return Markdown with these sections:

1. Primary Journey
2. Supporting Journeys
3. Edge Cases
4. User Decisions
5. Journey Assumptions

## Validation Checklist

- Journeys map to product goals.
- Each journey has a clear start and end.
- Optional details do not become blocking requirements.
