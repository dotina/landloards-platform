"""Pure-unit tests for payment plans."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.plans.schemas import Installment, PlanDecision, PlanRequest


def _inst(d: str, a: str) -> Installment:
    return Installment(date=date.fromisoformat(d), amount=Decimal(a))


def test_plan_request_requires_at_least_one_installment() -> None:
    with pytest.raises(ValidationError):
        PlanRequest(invoice_id="00000000-0000-0000-0000-000000000001", schedule=[])


def test_plan_request_dates_strictly_increasing() -> None:
    with pytest.raises(ValidationError):
        PlanRequest(
            invoice_id="00000000-0000-0000-0000-000000000001",
            schedule=[_inst("2026-05-15", "1000"), _inst("2026-05-10", "1000")],
        )
    with pytest.raises(ValidationError):
        PlanRequest(
            invoice_id="00000000-0000-0000-0000-000000000001",
            schedule=[_inst("2026-05-15", "1000"), _inst("2026-05-15", "1000")],
        )


def test_plan_request_max_12_installments() -> None:
    """Schema caps schedule at 12 entries (one year)."""
    # Build 13 strictly-increasing dates without overflowing the calendar.
    items = [_inst(f"2026-01-{d:02d}", "100") for d in range(1, 14)]
    with pytest.raises(ValidationError):
        PlanRequest(
            invoice_id="00000000-0000-0000-0000-000000000001", schedule=items
        )


def test_plan_decision_counter_requires_counter_schedule() -> None:
    with pytest.raises(ValidationError):
        PlanDecision(action="counter")


def test_plan_decision_counter_schedule_only_with_counter() -> None:
    with pytest.raises(ValidationError):
        PlanDecision(
            action="approve",
            counter_schedule=[_inst("2026-05-15", "100")],
        )


def test_plan_decision_approve_ok() -> None:
    PlanDecision(action="approve")


def test_app_router_has_plans_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/plans" in paths
    assert "/plans/me" in paths
    assert "/admin/plans" in paths
    assert "/admin/plans/{plan_id}/decision" in paths
