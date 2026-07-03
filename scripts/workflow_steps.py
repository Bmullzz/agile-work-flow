"""Canonical workflow step registry."""

from __future__ import annotations

from scripts.models import WorkflowStep


WORKFLOW_STEPS = [
    WorkflowStep(
        step_number=0,
        step_id="00-app-intake",
        name="App Intake",
        prompt_template_path="prompts/00-app-intake.md",
        output_path="00-intake/00-app-intake.md",
        depends_on_step_ids=[],
        required_sections=[
            "Summary",
            "Target Users",
            "Problem Statement",
            "Proposed Solution",
            "Assumptions",
        ],
    ),
    WorkflowStep(
        step_number=1,
        step_id="01-product-vision",
        name="Product Vision",
        prompt_template_path="prompts/01-product-vision.md",
        output_path="01-product/01-product-vision.md",
        depends_on_step_ids=["00-app-intake"],
        required_sections=[
            "Product Vision",
            "Primary Users",
            "Value Proposition",
            "MVP Success Criteria",
            "Non-Goals",
        ],
    ),
    WorkflowStep(
        step_number=2,
        step_id="02-tech-stack",
        name="Tech Stack",
        prompt_template_path="prompts/02-tech-stack.md",
        output_path="02-technical/02-tech-stack.md",
        depends_on_step_ids=["00-app-intake", "01-product-vision"],
        required_sections=[
            "Recommended Stack",
            "Rationale",
            "Development Tooling",
            "Testing Approach",
        ],
    ),
    WorkflowStep(
        step_number=3,
        step_id="03-system-architecture",
        name="System Architecture",
        prompt_template_path="prompts/03-system-architecture.md",
        output_path="02-technical/03-system-architecture.md",
        depends_on_step_ids=["01-product-vision", "02-tech-stack"],
        required_sections=[
            "Architecture Overview",
            "Components",
            "Data Flow",
            "Key Interfaces",
        ],
    ),
    WorkflowStep(
        step_number=4,
        step_id="04-user-journeys",
        name="User Journeys",
        prompt_template_path="prompts/04-user-journeys.md",
        output_path="03-discovery/04-user-journeys.md",
        depends_on_step_ids=[
            "00-app-intake",
            "01-product-vision",
            "03-system-architecture",
        ],
        required_sections=[
            "Primary Journey",
            "Supporting Journeys",
            "Edge Cases",
            "User Decisions",
        ],
    ),
    WorkflowStep(
        step_number=5,
        step_id="05-epics",
        name="Epics",
        prompt_template_path="prompts/05-epics.md",
        output_path="03-discovery/05-epics.md",
        depends_on_step_ids=[
            "01-product-vision",
            "03-system-architecture",
            "04-user-journeys",
        ],
        required_sections=[
            "Epic Summary",
            "Epics",
            "Acceptance Signals",
            "Out of Scope",
        ],
    ),
    WorkflowStep(
        step_number=6,
        step_id="06-product-user-stories",
        name="Product User Stories",
        prompt_template_path="prompts/06-product-user-stories.md",
        output_path="04-stories/06-product-user-stories.md",
        depends_on_step_ids=[
            "00-app-intake",
            "01-product-vision",
            "05-epics",
        ],
        required_sections=[
            "Story List",
            "Acceptance Criteria",
            "Dependencies",
            "Assumptions",
        ],
    ),
    WorkflowStep(
        step_number=7,
        step_id="07-technical-stories",
        name="Technical Stories",
        prompt_template_path="prompts/07-technical-stories.md",
        output_path="04-stories/07-technical-stories.md",
        depends_on_step_ids=[
            "01-product-vision",
            "02-tech-stack",
            "03-system-architecture",
            "06-product-user-stories",
        ],
        required_sections=[
            "Technical Story List",
            "Acceptance Criteria",
            "Traceability",
            "Risks",
        ],
    ),
    WorkflowStep(
        step_number=8,
        step_id="08-stories-by-application-layer",
        name="Stories by Application Layer",
        prompt_template_path="prompts/08-stories-by-application-layer.md",
        output_path="04-stories/08-stories-by-application-layer.md",
        depends_on_step_ids=["03-system-architecture", "07-technical-stories"],
        required_sections=[
            "Layer Overview",
            "Stories by Layer",
            "Cross-Layer Work",
            "Sequencing Notes",
        ],
    ),
    WorkflowStep(
        step_number=9,
        step_id="09-dependency-analysis",
        name="Dependency Analysis",
        prompt_template_path="prompts/09-dependency-analysis.md",
        output_path="05-planning/09-dependency-analysis.md",
        depends_on_step_ids=[
            "03-system-architecture",
            "07-technical-stories",
            "08-stories-by-application-layer",
        ],
        required_sections=[
            "Dependency Summary",
            "Dependency Table",
            "Parallelizable Work",
            "Blockers and Risks",
            "Recommended Order",
        ],
    ),
    WorkflowStep(
        step_number=10,
        step_id="10-phased-roadmap",
        name="Phased Roadmap",
        prompt_template_path="prompts/10-phased-roadmap.md",
        output_path="05-planning/10-phased-roadmap.md",
        depends_on_step_ids=[
            "01-product-vision",
            "07-technical-stories",
            "09-dependency-analysis",
        ],
        required_sections=[
            "Roadmap Overview",
            "Phases",
            "Phase Goals",
            "Included Stories",
            "Exit Criteria",
        ],
    ),
    WorkflowStep(
        step_number=11,
        step_id="11-coding-agent-optimized-stories",
        name="Coding-Agent-Optimized Stories",
        prompt_template_path="prompts/11-coding-agent-optimized-stories.md",
        output_path="06-agent-prompts/11-coding-agent-optimized-stories.md",
        depends_on_step_ids=[
            "07-technical-stories",
            "09-dependency-analysis",
            "10-phased-roadmap",
        ],
        required_sections=[
            "Optimized Stories",
            "Inputs Needed",
            "Files to Create or Modify",
            "Acceptance Criteria",
            "Test Expectations",
        ],
    ),
    WorkflowStep(
        step_number=12,
        step_id="12-coding-agent-prompts",
        name="Coding-Agent Prompts",
        prompt_template_path="prompts/12-coding-agent-prompts.md",
        output_path="06-agent-prompts/12-coding-agent-prompts.md",
        depends_on_step_ids=[
            "07-technical-stories",
            "10-phased-roadmap",
            "11-coding-agent-optimized-stories",
        ],
        required_sections=[
            "Prompt Index",
            "Coding Agent Prompts",
            "Shared Context",
            "Validation Notes",
        ],
    ),
    WorkflowStep(
        step_number=13,
        step_id="13-project-setup-prompt",
        name="Project Setup Prompt",
        prompt_template_path="prompts/13-project-setup-prompt.md",
        output_path="06-agent-prompts/13-project-setup-prompt.md",
        depends_on_step_ids=[
            "01-product-vision",
            "02-tech-stack",
            "03-system-architecture",
            "10-phased-roadmap",
        ],
        required_sections=[
            "Objective",
            "Context",
            "Files to Create or Modify",
            "Implementation Steps",
            "Verification",
            "Definition of Done",
        ],
    ),
    WorkflowStep(
        step_number=14,
        step_id="14-qa-validation-plan",
        name="QA Validation Plan",
        prompt_template_path="prompts/14-qa-validation-plan.md",
        output_path="07-quality/14-qa-validation-plan.md",
        depends_on_step_ids=[
            "01-product-vision",
            "07-technical-stories",
            "09-dependency-analysis",
            "10-phased-roadmap",
        ],
        required_sections=[
            "QA Strategy",
            "Test Areas",
            "Acceptance Checks",
            "Regression Risks",
            "Manual Review Checklist",
        ],
    ),
    WorkflowStep(
        step_number=15,
        step_id="15-documentation-plan",
        name="Documentation Plan",
        prompt_template_path="prompts/15-documentation-plan.md",
        output_path="08-documentation/15-documentation-plan.md",
        depends_on_step_ids=[
            "01-product-vision",
            "02-tech-stack",
            "03-system-architecture",
            "10-phased-roadmap",
        ],
        required_sections=[
            "Documentation Goals",
            "Required Documents",
            "Audience and Purpose",
            "Maintenance Notes",
            "Documentation Checklist",
        ],
    ),
]


def get_step_by_id(step_id: str) -> WorkflowStep:
    for step in WORKFLOW_STEPS:
        if step.step_id == step_id:
            return step
    raise KeyError(f"Unknown workflow step ID: {step_id}")


def get_steps_from(step_id: str) -> list[WorkflowStep]:
    step = get_step_by_id(step_id)
    return WORKFLOW_STEPS[step.step_number :]


def get_single_step(step_id: str) -> list[WorkflowStep]:
    return [get_step_by_id(step_id)]
