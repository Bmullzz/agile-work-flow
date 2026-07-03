# Project Setup Prompt

## Role

You are a senior developer creating repository setup instructions.

## Task

Create the first coding-agent prompt for project setup.

## Input Context

- Product vision: `{{PRODUCT_VISION}}`
- Tech stack: `{{TECH_STACK}}`
- System architecture: `{{SYSTEM_ARCHITECTURE}}`
- Phased roadmap: `{{PHASED_ROADMAP}}`

## Instructions

- Define the initial repository structure and setup commands.
- Keep the setup prompt minimal and runnable.
- Include verification steps.

## Required Output Format

Return Markdown with these sections:

1. Objective
2. Context
3. Files to Create or Modify
4. Implementation Steps
5. Verification
6. Definition of Done

## Validation Checklist

- Setup is aligned with the selected stack.
- Verification can run locally.
- The prompt avoids future-phase scope.
