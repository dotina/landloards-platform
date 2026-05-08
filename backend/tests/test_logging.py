"""Tests for structlog configuration."""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from app.core.logging import configure_logging, get_logger


def test_configure_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    """After configure_logging, log records must be valid JSON on stdout."""
    configure_logging(level="INFO")
    log = get_logger("test")
    log.info("hello", request_id="abc-123", user="bob")

    captured = capsys.readouterr().out.strip().splitlines()
    assert captured, "expected at least one log line"
    record = json.loads(captured[-1])

    assert record["event"] == "hello"
    assert record["request_id"] == "abc-123"
    assert record["user"] == "bob"
    assert record["level"] == "info"


def test_configure_logging_respects_level(capsys: pytest.CaptureFixture[str]) -> None:
    """DEBUG records must be filtered out at INFO level."""
    configure_logging(level="INFO")
    log = get_logger("test")
    log.debug("should-not-appear")
    log.info("should-appear")

    out = capsys.readouterr().out
    assert "should-not-appear" not in out
    assert "should-appear" in out


def test_configure_logging_emits_iso_utc_timestamp(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Each record must carry a parseable ISO-8601 UTC timestamp."""
    configure_logging(level="INFO")
    log = get_logger("test")
    log.info("with-timestamp")

    record = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert "timestamp" in record
    parsed = datetime.fromisoformat(record["timestamp"])
    assert parsed.tzinfo is not None, "timestamp must include timezone"


def test_get_logger_seeds_context_from_kwargs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Initial values passed to get_logger appear on every record."""
    configure_logging(level="INFO")
    log = get_logger("test", request_id="seed-abc")
    log.info("event-1")
    log.info("event-2")

    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) >= 2
    for line in lines[-2:]:
        assert json.loads(line)["request_id"] == "seed-abc"


def test_configure_logging_rejects_invalid_level() -> None:
    """Unknown levels must raise rather than silently fall back to INFO."""
    with pytest.raises(ValueError, match="Invalid log level"):
        configure_logging(level="WARNNG")
