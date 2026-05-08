"""Tests for structlog configuration."""
from __future__ import annotations

import json
import logging

import pytest


def test_configure_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    """After configure_logging, log records must be valid JSON on stdout."""
    from app.core.logging import configure_logging, get_logger

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
    from app.core.logging import configure_logging, get_logger

    configure_logging(level="INFO")
    log = get_logger("test")
    log.debug("should-not-appear")
    log.info("should-appear")

    out = capsys.readouterr().out
    assert "should-not-appear" not in out
    assert "should-appear" in out
