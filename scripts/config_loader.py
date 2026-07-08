"""Configuration loading and validation for the local workflow runtime."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Union

import yaml


REQUIRED_SECTIONS = ("llm", "workflow", "output", "prompts")
SECRET_KEY_NAMES = {"api_key", "apikey", "openai_api_key", "secret", "token"}

DEFAULT_CONFIG: dict[str, Any] = {
    "generation": {
        "backend": "openai_api",
    },
    "backends": {
        "openai_api": {},
        "mock": {},
        "manual_chatgpt": {},
        "codex": {},
    },
    "llm": {
        "provider": "openai",
        "model": "gpt-4.1-mini",
        "temperature": 0.2,
        "max_retries": 2,
        "retry_delay_seconds": 0,
        "timeout_seconds": 60,
    },
    "workflow": {
        "default_review": False,
        "resume_enabled": True,
        "stop_on_failure": True,
        "fail_on_warnings": False,
        "steps": [],
    },
    "output": {
        "format": "markdown",
        "create_run_directory": True,
        "overwrite": False,
    },
    "prompts": {
        "directory": "prompts",
        "extension": ".md",
    },
}


class ConfigError(ValueError):
    """Raised when configuration content is invalid."""


def load_config(path: Union[str, Path]) -> dict[str, Any]:
    """Load and validate non-secret runtime settings from a YAML file."""
    config_path = Path(path)
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")

    try:
        with config_path.open("r", encoding="utf-8") as file:
            raw_config = yaml.safe_load(file)
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid YAML in config file {config_path}: {error}") from error

    if raw_config is None:
        raw_config = {}
    if not isinstance(raw_config, dict):
        raise ConfigError("Config file must contain a top-level mapping.")

    _validate_required_sections(raw_config)
    _validate_no_secrets(raw_config)

    config = deepcopy(DEFAULT_CONFIG)
    _deep_update(config, raw_config)
    return config


def _validate_required_sections(config: dict[str, Any]) -> None:
    for section in REQUIRED_SECTIONS:
        if section not in config:
            raise ConfigError(f"Missing required config section: {section}")
        if not isinstance(config[section], dict):
            raise ConfigError(f"Config section '{section}' must be a mapping.")


def _validate_no_secrets(value: Any, path: tuple[str, ...] = ()) -> None:
    if isinstance(value, dict):
        for key, nested_value in value.items():
            normalized_key = str(key).lower().replace("-", "_")
            current_path = path + (str(key),)
            if normalized_key in SECRET_KEY_NAMES:
                joined_path = ".".join(current_path)
                raise ConfigError(
                    f"Secret-like setting '{joined_path}' must not be stored in config.yaml."
                )
            _validate_no_secrets(nested_value, current_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _validate_no_secrets(item, path + (str(index),))


def _deep_update(base: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, value in overrides.items():
        if value is None and isinstance(base.get(key), dict):
            continue
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_update(base[key], value)
        else:
            base[key] = value
