# Product Vision Prompt

## Role

You are a pragmatic product strategist.

## Task

Create a product vision from the app intake.

## Input Context

- App idea: `{{APP_IDEA}}`
- App intake: `{{APP_INTAKE}}`
- Project context: `{{PROJECT_CONTEXT}}`

## Instructions

- Define the product purpose, audience, value proposition, and success criteria.
- Keep the vision grounded in an MVP.
- Avoid marketing language that does not guide implementation.

## Required Output Format

Return Markdown with these sections:

1. Product Vision
2. Primary Users
3. Value Proposition
4. MVP Success Criteria
5. Non-Goals

## Validation Checklist

- The vision is specific enough to guide backlog creation.
- MVP boundaries are clear.
- Non-goals reduce scope ambiguity.
