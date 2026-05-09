"""Pure-function invoice state machine.

Implements the diagram in design §4.4. The service layer calls
``transition`` with a current status and an event; this module never
touches the database.

Events
------
- ``partial_pay``           — a successful payment landed but doesn't cover total.
- ``full_pay``              — a successful payment brings outstanding to 0.
- ``pass_due_grace``        — `dueDate + graceDays` reached without full payment.
- ``plan_approved``         — landlord approved a payment plan on this invoice.
- ``plan_installment_missed`` — at least one scheduled installment overdue 24h.
- ``plan_completed``        — all plan installments paid in full.
- ``write_off``             — landlord admin action; terminal.
"""
from __future__ import annotations

from typing import Final, FrozenSet, Literal

from app.invoices.models import InvoiceStatus

InvoiceEvent = Literal[
    "partial_pay",
    "full_pay",
    "pass_due_grace",
    "plan_approved",
    "plan_installment_missed",
    "plan_completed",
    "write_off",
]


class IllegalStateError(ValueError):
    """Raised when an event is not valid in the current invoice state."""

    def __init__(self, *, current: InvoiceStatus, event: InvoiceEvent) -> None:
        super().__init__(
            f"illegal invoice transition: cannot apply {event!r} to {current.value!r}"
        )
        self.current = current
        self.event = event


# Allowed (status, event) → next-status mapping. Anything not in the table
# is illegal.
_TRANSITIONS: Final[dict[tuple[InvoiceStatus, InvoiceEvent], InvoiceStatus]] = {
    # ── from OPEN ──────────────────────────────────────────────
    (InvoiceStatus.OPEN, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.OPEN, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.OPEN, "pass_due_grace"): InvoiceStatus.OVERDUE,
    (InvoiceStatus.OPEN, "write_off"): InvoiceStatus.WRITTEN_OFF,
    # ── from PARTIAL ───────────────────────────────────────────
    (InvoiceStatus.PARTIAL, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.PARTIAL, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.PARTIAL, "pass_due_grace"): InvoiceStatus.OVERDUE,
    (InvoiceStatus.PARTIAL, "plan_approved"): InvoiceStatus.ON_PAY_PLAN,
    (InvoiceStatus.PARTIAL, "write_off"): InvoiceStatus.WRITTEN_OFF,
    # ── from OVERDUE ───────────────────────────────────────────
    (InvoiceStatus.OVERDUE, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.OVERDUE, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.OVERDUE, "plan_approved"): InvoiceStatus.ON_PAY_PLAN,
    (InvoiceStatus.OVERDUE, "write_off"): InvoiceStatus.WRITTEN_OFF,
    # ── from ON_PAY_PLAN ──────────────────────────────────────
    (InvoiceStatus.ON_PAY_PLAN, "plan_completed"): InvoiceStatus.PAID,
    (InvoiceStatus.ON_PAY_PLAN, "plan_installment_missed"): InvoiceStatus.DEFAULTED,
    (InvoiceStatus.ON_PAY_PLAN, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.ON_PAY_PLAN, "write_off"): InvoiceStatus.WRITTEN_OFF,
    # ── from DEFAULTED ────────────────────────────────────────
    (InvoiceStatus.DEFAULTED, "partial_pay"): InvoiceStatus.PARTIAL,
    (InvoiceStatus.DEFAULTED, "full_pay"): InvoiceStatus.PAID,
    (InvoiceStatus.DEFAULTED, "write_off"): InvoiceStatus.WRITTEN_OFF,
    # ── PAID and WRITTEN_OFF are terminal (no exits) ──────────
}


# Convenience: states from which a payment plan can be requested.
PLAN_ELIGIBLE_STATES: Final[FrozenSet[InvoiceStatus]] = frozenset(
    {InvoiceStatus.OVERDUE, InvoiceStatus.PARTIAL}
)


# Terminal states — never transition out.
TERMINAL_STATES: Final[FrozenSet[InvoiceStatus]] = frozenset(
    {InvoiceStatus.PAID, InvoiceStatus.WRITTEN_OFF}
)


def next_status(current: InvoiceStatus, event: InvoiceEvent) -> InvoiceStatus:
    """Return the resulting status. Raises ``IllegalStateError`` on disallowed events."""
    if (current, event) not in _TRANSITIONS:
        raise IllegalStateError(current=current, event=event)
    return _TRANSITIONS[(current, event)]
