"""Tests for invoice period computation."""
from __future__ import annotations

from datetime import date

from app.invoices.service import compute_period_for


def test_period_runs_first_to_last_of_month() -> None:
    s, e, due = compute_period_for(today=date(2026, 5, 12), due_day=1)
    assert s == date(2026, 5, 1)
    assert e == date(2026, 5, 31)
    assert due == date(2026, 5, 1)


def test_due_day_clamped_to_last_of_short_months() -> None:
    s, e, due = compute_period_for(today=date(2026, 2, 1), due_day=31)
    assert s == date(2026, 2, 1)
    assert e == date(2026, 2, 28)
    assert due == date(2026, 2, 28)


def test_due_day_clamped_in_leap_february() -> None:
    _s, e, due = compute_period_for(today=date(2024, 2, 1), due_day=31)
    assert e == date(2024, 2, 29)
    assert due == date(2024, 2, 29)


def test_app_router_has_invoice_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/invoices" in paths
    assert "/invoices/{invoice_id}" in paths
    assert "/admin/invoices/{invoice_id}/write-off" in paths
    assert "/tenant/invoices" in paths
