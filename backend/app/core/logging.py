"""Structured logging via structlog, JSON output to stdout."""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import FilteringBoundLogger

_VALID_LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def configure_logging(level: str = "INFO") -> None:
    """Configure structlog and stdlib logging for the whole app.

    Idempotent: re-calling replaces the prior configuration. Loggers
    obtained via ``get_logger`` after the call see the new settings.
    """
    level_upper = level.upper()
    if level_upper not in _VALID_LEVELS:
        raise ValueError(
            f"Invalid log level {level!r}; expected one of {list(_VALID_LEVELS)}"
        )
    log_level = getattr(logging, level_upper)

    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
        force=True,
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
    )


def get_logger(name: str | None = None, **initial_values: Any) -> FilteringBoundLogger:
    """Return a bound logger; pass keyword args to seed context."""
    return structlog.get_logger(name).bind(**initial_values)
