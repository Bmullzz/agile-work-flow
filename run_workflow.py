#!/usr/bin/env python3
"""Local CLI entry point for the AI Agile Workflow MVP."""

from __future__ import annotations

import argparse
from pathlib import Path

try:
    import yaml
except ModuleNotFoundError:
    yaml = None


ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = ROOT_DIR / "config.yaml"


def load_config(path: Path) -> dict:
    """Load YAML configuration from disk."""
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    content = path.read_text(encoding="utf-8")

    if yaml is not None:
        return yaml.safe_load(content) or {}

    config = {}
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, separator, value = stripped.partition(":")
        if not separator:
            raise ValueError(
                "PyYAML is not installed and config fallback only supports "
                f"'key: value' entries. Invalid line: {line}"
            )
        config[key.strip()] = value.strip().strip("\"'")
    return config


def read_app_idea(path: Path) -> str:
    """Read the input application idea markdown file."""
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    return path.read_text(encoding="utf-8").strip()


def run_workflow(config_path: Path) -> None:
    config = load_config(config_path)

    input_path = ROOT_DIR / config.get("input_file", "input/app-idea.md")
    output_dir = ROOT_DIR / config.get("output_dir", "output")
    output_dir.mkdir(parents=True, exist_ok=True)

    app_idea = read_app_idea(input_path)

    print("AI Agile Workflow MVP")
    print(f"Config: {config_path}")
    print(f"Input: {input_path}")
    print(f"Output: {output_dir}")
    print()
    print("Loaded app idea:")
    print(app_idea if app_idea else "(empty)")
    print()
    print("Workflow generation is not implemented yet.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local AI Agile Workflow MVP pipeline."
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


def print_runtime_options(args: argparse.Namespace) -> None:
    print("AI Agile Workflow MVP")
    print(f"Input: {args.input.resolve()}")
    print(f"Output: {args.output.resolve()}")
    print(f"Mock LLM: {args.mock_llm}")
    print(f"Review: {args.review}")
    print(f"No review: {args.no_review}")
    print(f"Resume: {args.resume}")
    print(f"Overwrite: {args.overwrite}")
    print(f"From step: {args.from_step}")
    print(f"Step: {args.step}")
    print()
    print("Workflow execution is not implemented yet.")


def main() -> None:
    args = parse_args()
    print_runtime_options(args)


if __name__ == "__main__":
    main()
