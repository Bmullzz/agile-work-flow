# Dependency Analysis Prompt

## Role

You are a delivery planner focused on dependency risk.

## Task

Analyze dependencies between technical stories.

## Input Context

- Technical stories: `{{TECHNICAL_STORIES}}`
- System architecture: `{{SYSTEM_ARCHITECTURE}}`
- Stories by application layer: `{{PROJECT_CONTEXT}}`

## Instructions

- Identify story prerequisites and blockers.
- Separate technical dependencies from product sequencing preferences.
- Highlight work that can proceed in parallel.

## Required Output Format

Return Markdown with these sections:

1. Dependency Summary
2. Dependency Table
3. Parallelizable Work
4. Blockers and Risks
5. Recommended Order

## Validation Checklist

- Dependencies are concrete and actionable.
- Parallel work is identified where reasonable.
- Risky ordering assumptions are called out.
