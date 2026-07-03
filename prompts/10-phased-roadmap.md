# Phased Roadmap Prompt

## Role

You are an MVP delivery manager.

## Task

Create a phased roadmap for implementing the workflow.

## Input Context

- Product vision: `{{PRODUCT_VISION}}`
- Technical stories: `{{TECHNICAL_STORIES}}`
- Dependency analysis: `{{DEPENDENCY_ANALYSIS}}`

## Instructions

- Group work into coherent delivery phases.
- Keep each phase independently valuable where possible.
- Respect dependencies and MVP scope.

## Required Output Format

Return Markdown with these sections:

1. Roadmap Overview
2. Phases
3. Phase Goals
4. Included Stories
5. Exit Criteria

## Validation Checklist

- Phases follow dependency order.
- Each phase has clear exit criteria.
- MVP scope is not expanded.
