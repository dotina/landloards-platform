"""Unit tests for C2B helpers + route registration."""
from __future__ import annotations

from datetime import UTC
from decimal import Decimal

import app.core.all_models  # noqa: F401
from app.core.models import Base
from app.payments.c2b import _parse_trans_time, _safe_decimal


def test_parse_trans_time_valid() -> None:
    dt = _parse_trans_time("20260509153045")
    assert dt is not None
    assert dt.year == 2026 and dt.month == 5 and dt.day == 9
    assert dt.tzinfo == UTC


def test_parse_trans_time_garbage() -> None:
    assert _parse_trans_time("not-a-date") is None
    assert _parse_trans_time(None) is None
    assert _parse_trans_time("") is None


def test_safe_decimal_handles_strings_and_floats() -> None:
    assert _safe_decimal("12345.50") == Decimal("12345.50")
    assert _safe_decimal(123) == Decimal("123")
    assert _safe_decimal("oops") == Decimal("0")
    assert _safe_decimal(None) == Decimal("0")


def test_unmatched_c2b_table_registered() -> None:
    assert "unmatched_c2b" in Base.metadata.tables


def test_unmatched_c2b_unique_receipt() -> None:
    t = Base.metadata.tables["unmatched_c2b"]
    assert any(c.name == "uq_unmatched_c2b_receipt" for c in t.constraints if c.name)


def test_app_router_has_c2b_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/webhooks/mpesa/c2b/validate" in paths
    assert "/webhooks/mpesa/c2b/confirm" in paths
    assert "/admin/payments/c2b/unmatched" in paths
    assert "/admin/payments/c2b/unmatched/{unmatched_id}/allocate" in paths
