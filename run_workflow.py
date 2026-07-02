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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the local AI Agile Workflow MVP pipeline."
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the YAML config file.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_workflow(args.config.resolve())


if __name__ == "__main__":
    main()
