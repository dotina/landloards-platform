"""Exhaustive invoice state-machine tests (design §4.4 & §7).

Every legal transition in the diagram is verified, and every other
(state, event) combination must raise ``IllegalStateError``.
"""
from __future__ import annotations

import pytest

from app.invoices.models import InvoiceStatus
from app.invoices.state_machine import (
    _TRANSITIONS,
    PLAN_ELIGIBLE_STATES,
    TERMINAL_STATES,
    IllegalStateError,
    InvoiceEvent,
    next_status,
)

ALL_EVENTS: tuple[InvoiceEvent, ...] = (
    "partial_pay",
    "full_pay",
    "pass_due_grace",
    "plan_approved",
    "plan_installment_missed",
    "plan_completed",
    "write_off",
)

# Ground-truth table from design §4.4. Every entry MUST match _TRANSITIONS.
EXPECTED_LEGAL: dict[tuple[InvoiceStatus, InvoiceEvent], InvoiceStatus] = {
    (InvoiceStatus.OPEN, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.OPEN, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.OPEN, "pass_due_grace"): InvoiceStatus.OVERDUE,
    (InvoiceStatus.OPEN, "write_off"): InvoiceStatus.WRITTEN_OFF,
    (InvoiceStatus.PARTIAL, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.PARTIAL, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.PARTIAL, "pass_due_grace"): InvoiceStatus.OVERDUE,
    (InvoiceStatus.PARTIAL, "plan_approved"): InvoiceStatus.ON_PAY_PLAN,
    (InvoiceStatus.PARTIAL, "write_off"): InvoiceStatus.WRITTEN_OFF,
    (InvoiceStatus.OVERDUE, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.OVERDUE, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.OVERDUE, "plan_approved"): InvoiceStatus.ON_PAY_PLAN,
    (InvoiceStatus.OVERDUE, "write_off"): InvoiceStatus.WRITTEN_OFF,
    (InvoiceStatus.ON_PAY_PLAN, "plan_completed"): InvoiceStatus.PAID,
    (InvoiceStatus.ON_PAY_PLAN, "plan_installment_missed"): InvoiceStatus.DEFAULTED,
    (InvoiceStatus.ON_PAY_PLAN, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.ON_PAY_PLAN, "write_off"): InvoiceStatus.WRITTEN_OFF,
    (InvoiceStatus.DEFAULTED, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.DEFAULTED, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.DEFAULTED, "write_off"): InvoiceStatus.WRITTEN_OFF,
}


@pytest.mark.parametrize(("from_status", "event", "to_status"),
                         [(s, e, t) for (s, e), t in EXPECTED_LEGAL.items()])
def test_legal_transition(
    from_status: InvoiceStatus, event: InvoiceEvent, to_status: InvoiceStatus
) -> None:
    """Every documented arrow in design §4.4 must hold."""
    assert next_status(from_status, event) == to_status


def test_module_table_matches_expected() -> None:
    """Sanity: the module's _TRANSITIONS must equal the design table."""
    assert _TRANSITIONS == EXPECTED_LEGAL


@pytest.mark.parametrize("from_status", list(InvoiceStatus))
@pytest.mark.parametrize("event", ALL_EVENTS)
def test_unknown_combinations_raise(
    from_status: InvoiceStatus, event: InvoiceEvent
) -> None:
    """Every combo not in EXPECTED_LEGAL must be rejected."""
    if (from_status, event) in EXPECTED_LEGAL:
        return  # legal — handled by parametrize above
    with pytest.raises(IllegalStateError):
        next_status(from_status, event)


def test_terminal_states_have_no_exits() -> None:
    """PAID and WRITTEN_OFF are absorbing — every event raises."""
    for state in TERMINAL_STATES:
        for event in ALL_EVENTS:
            with pytest.raises(IllegalStateError):
                next_status(state, event)


def test_plan_eligible_states_match_design() -> None:
    """Per design §4.5: only OVERDUE or PARTIAL invoices accept plan requests."""
    assert PLAN_ELIGIBLE_STATES == {InvoiceStatus.OVERDUE, InvoiceStatus.PARTIAL}
