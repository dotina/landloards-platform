"""Late-fee accrual logic.

A pure helper computes the *target* accrued late fee for an invoice
given its rule + cadence + cap; the job updates the row to that amount.

Design constraints (§4.2 + plan §11):

- ``on_pay_plan`` invoices skip accrual entirely (resumes on default).
- Cap: never accrue more than ``rent_amount * cap_months``.
- Cadence:
    * ``once``    — accrue once at grace boundary.
    * ``daily``   — accrue per day past grace.
    * ``monthly`` — accrue per month past grace.
- Type:
    * ``flat``    — `value` is the per-period KES amount.
    * ``percent`` — `value` is % of `rent_amount` per period.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from app.invoices.models import Invoice, InvoiceStatus


@dataclass(frozen=True, slots=True)
class LateFeeParams:
    type_: str  # "flat" | "percent"
    value: Decimal
    cadence: str  # "once" | "daily" | "monthly"
    grace_days: int
    cap_months: int

    @classmethod
    def from_jsonb(cls, raw: dict[str, Any]) -> LateFeeParams:
        return cls(
            type_=raw["type"],
            value=Decimal(str(raw["value"])),
            cadence=raw["cadence"],
            grace_days=int(raw.get("graceDays", raw.get("grace_days", 0))),
            cap_months=int(raw.get("capMonths", raw.get("cap_months", 1))),
        )


def periods_past_grace(today: date, due_date: date, params: LateFeeParams) -> int:
    """Return count of accrual periods past grace; 0 if before grace boundary."""
    boundary = due_date + timedelta(days=params.grace_days)
    if today < boundary:
        return 0
    delta_days = (today - boundary).days
    if params.cadence == "once":
        return 1
    if params.cadence == "daily":
        return delta_days + 1
    # "monthly": count whole 30-day blocks (simple, predictable, mismatched
    # actual months are unproblematic given typical 1-3 month leases).
    return (delta_days // 30) + 1


def compute_target_accrued(
    *,
    rent_amount: Decimal,
    today: date,
    due_date: date,
    params: LateFeeParams,
) -> Decimal:
    """Return the target ``Invoice.late_fee_accrued`` for the given inputs."""
    n = periods_past_grace(today, due_date, params)
    if n <= 0:
        return Decimal("0")
    if params.type_ == "flat":
        per = params.value
    else:
        per = (rent_amount * params.value) / Decimal("100")
    raw = per * Decimal(n)
    cap = rent_amount * Decimal(params.cap_months)
    return min(raw, cap).quantize(Decimal("0.01"))


def should_accrue(invoice: Invoice) -> bool:
    """Skip terminal & on-plan states."""
    return invoice.status not in (
        InvoiceStatus.PAID,
        InvoiceStatus.WRITTEN_OFF,
        InvoiceStatus.ON_PAY_PLAN,
    )
