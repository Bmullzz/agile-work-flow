"""Central logging setup for workflow execution."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any


LOGGER_NAME = "ai_agile_workflow"
LOG_FILE_NAME = "workflow.log"


class RedactingFormatter(logging.Formatter):
    """Formatter that removes obvious secret values from log output."""

    def format(self, record: logging.LogRecord) -> str:
        copied_record = logging.makeLogRecord(record.__dict__.copy())
        copied_record.msg = redact_secrets(record.getMessage())
        copied_record.args = ()
        return super().format(copied_record)


def setup_workflow_logging(
    output_root: str | Path,
    level: int = logging.INFO,
    console: bool = True,
) -> tuple[logging.Logger, Path]:
    log_directory = Path(output_root) / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / LOG_FILE_NAME

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    _clear_handlers(logger)

    formatter = RedactingFormatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    return logger, log_path


def get_workflow_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)


def redact_secrets(value: Any) -> str:
    text = str(value)
    for secret in _secret_values():
        text = text.replace(secret, "[redacted]")
    text = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}\b", "[redacted]", text)
    text = re.sub(
        r"(?i)(api[_-]?key|token|secret)(\s*[=:]\s*)\S+",
        r"\1\2[redacted]",
        text,
    )
    return text


def _clear_handlers(logger: logging.Logger) -> None:
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()


def _secret_values() -> list[str]:
    secrets: list[str] = []
    for key, value in os.environ.items():
        normalized_key = key.lower()
        if not value or len(value) < 4:
            continue
        if any(marker in normalized_key for marker in ("api_key", "token", "secret")):
            secrets.append(value)
    return secrets
