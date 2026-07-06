#!/usr/bin/env python3
"""Local CLI entry point for the AI Agile Workflow MVP."""

from __future__ import annotations

import argparse
from pathlib import Path

from scripts.backends.base import GenerationBackendError
from scripts.backends.mock_backend import MockGenerationBackend
from scripts.backends.openai_api_backend import OpenAIAPIBackend
from scripts.config_loader import load_config
from scripts.logger import redact_secrets, setup_workflow_logging
from scripts.workflow_runner import WorkflowRunError, WorkflowRunner
from scripts.workflow_steps import WORKFLOW_STEPS, get_single_step, get_steps_from


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config.yaml"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local AI Agile Workflow MVP pipeline."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to the input app idea markdown file.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to the output directory for generated artifacts.",
    )
    parser.add_argument(
        "--mock-llm",
        action="store_true",
        help="Use mock LLM responses instead of real model calls.",
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Enable human review checkpoints.",
    )
    parser.add_argument(
        "--no-review",
        action="store_true",
        help="Disable human review checkpoints.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a previous workflow run.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing generated artifacts.",
    )
    parser.add_argument(
        "--from-step",
        help="Resume or start workflow execution from a named step.",
    )
    parser.add_argument(
        "--step",
        help="Run only a specific named workflow step.",
    )
    return parser.parse_args(argv)


def print_runtime_options(args: argparse.Namespace, step_count: int) -> None:
    print("AI Agile Workflow MVP")
    print(f"Config: {args.config.resolve()}")
    print(f"Input: {args.input.resolve()}")
    print(f"Output: {args.output.resolve()}")
    print(f"Mock LLM: {args.mock_llm}")
    print(f"Review: {args.review}")
    print(f"No review: {args.no_review}")
    print(f"Resume: {args.resume}")
    print(f"Overwrite: {args.overwrite}")
    print(f"From step: {args.from_step}")
    print(f"Step: {args.step}")
    print(f"Steps: {step_count}")


def select_workflow_steps(args: argparse.Namespace):
    if args.step:
        return get_single_step(args.step)
    if args.from_step:
        return get_steps_from(args.from_step)
    return WORKFLOW_STEPS


def create_generation_backend(args: argparse.Namespace, config: dict, logger=None):
    if args.mock_llm:
        return MockGenerationBackend()

    backend_name = (
        config.get("generation", {}).get("backend")
        or config.get("llm", {}).get("provider")
        or "openai_api"
    )
    if backend_name in {"openai", "openai_api"}:
        return OpenAIAPIBackend(config, logger=logger)
    if backend_name in {"mock", "mock_backend"}:
        return MockGenerationBackend()
    raise GenerationBackendError(
        f"Unknown generation backend '{backend_name}'. "
        "Supported backends: openai_api, mock."
    )


def main() -> None:
    args = parse_args()
    try:
        selected_steps = select_workflow_steps(args)
    except KeyError as error:
        raise SystemExit(str(error)) from error
    print_runtime_options(args, len(selected_steps))
    logger, log_path = setup_workflow_logging(args.output)
    logger.info("cli_start config=%s input=%s output=%s", args.config, args.input, args.output)
    logger.info("log_file path=%s", log_path)

    try:
        config = load_config(args.config)
    except Exception as error:
        logger.error("workflow_failure step=config error=%s", redact_secrets(error))
        raise SystemExit(str(error)) from error
    config.setdefault("output", {})["overwrite"] = args.overwrite
    if args.review:
        config.setdefault("workflow", {})["default_review"] = True
    if args.no_review:
        config.setdefault("workflow", {})["default_review"] = False
    try:
        generation_backend = create_generation_backend(args, config, logger=logger)
    except GenerationBackendError as error:
        logger.error("workflow_failure step=generation_backend error=%s", redact_secrets(error))
        raise SystemExit(str(error)) from error

    runner = WorkflowRunner(
        config=config,
        workflow_steps=WORKFLOW_STEPS,
        generation_backend=generation_backend,
    )

    try:
        result = runner.run(
            args.input,
            args.output,
            resume=args.resume,
            step_id=args.step,
            from_step_id=args.from_step,
            review=None,
        )
    except WorkflowRunError as error:
        logger.error("workflow_failure step=workflow error=%s", redact_secrets(error))
        raise SystemExit(str(error)) from error

    print()
    print(f"Completed {len(result.completed_step_ids)} workflow steps.")


if __name__ == "__main__":
    main()
