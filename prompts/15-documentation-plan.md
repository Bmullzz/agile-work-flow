# Documentation Plan Prompt

## Role

You are a technical writer planning developer-facing documentation.

## Task

Create a documentation plan for the MVP.

## Input Context

- Product vision: `{{PRODUCT_VISION}}`
- Tech stack: `{{TECH_STACK}}`
- System architecture: `{{SYSTEM_ARCHITECTURE}}`
- Phased roadmap: `{{PHASED_ROADMAP}}`

## Instructions

- Identify documents needed for setup, usage, configuration, and maintenance.
- Keep documentation scoped to what exists or is planned for the MVP.
- Include update triggers so docs stay current.

## Required Output Format

Return Markdown with these sections:

1. Documentation Goals
2. Required Documents
3. Audience and Purpose
4. Maintenance Notes
5. Documentation Checklist

## Validation Checklist

- Docs cover setup and CLI usage.
- Configuration and prompt editing are addressed.
- Maintenance responsibilities are clear.
