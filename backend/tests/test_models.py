"""Smoke tests for ORM models — invariants verifiable without a live DB.

Integration tests that hit a real Postgres via testcontainers are added
in a follow-up commit once Docker availability is wired into CI.
"""
from __future__ import annotations

import app.core.all_models  # noqa: F401  side-effect: register all models
from app.core.models import Base


def test_metadata_has_all_design_section_3_1_tables() -> None:
    """Every entity from design §3.1 has a table registered."""
    expected = {
        "users",
        "properties",
        "units",
        "tenants",
        "leases",
        "invoices",
        "payments",
        "payment_plans",
        "notification_log",
        "audit_event",
    }
    actual = {t.name for t in Base.metadata.sorted_tables}
    assert expected.issubset(actual), f"missing: {expected - actual}"


def test_payments_has_partial_unique_indexes() -> None:
    """Design §3.2: idempotency partial indexes on payments table."""
    payments = Base.metadata.tables["payments"]
    index_names = {idx.name for idx in payments.indexes}
    assert "uq_payments_channel_mpesa_receipt" in index_names
    assert "uq_payments_checkout_request_id" in index_names

    receipt_idx = next(
        idx for idx in payments.indexes if idx.name == "uq_payments_channel_mpesa_receipt"
    )
    assert receipt_idx.unique is True
    assert receipt_idx.dialect_options["postgresql"]["where"] is not None

    co_idx = next(
        idx for idx in payments.indexes if idx.name == "uq_payments_checkout_request_id"
    )
    assert co_idx.unique is True
    assert co_idx.dialect_options["postgresql"]["where"] is not None


def test_invoices_unique_lease_period() -> None:
    """Generator must be idempotent — one invoice per (lease_id, period_start)."""
    invoices = Base.metadata.tables["invoices"]
    constraint_names = {c.name for c in invoices.constraints}
    assert "uq_invoices_lease_period" in constraint_names


def test_units_due_day_check_constraint() -> None:
    """Unit.due_day_of_month must be 1..28 (no surprise February)."""
    units = Base.metadata.tables["units"]
    constraint_names = {c.name for c in units.constraints if c.name}
    assert "ck_units_due_day_range" in constraint_names


def test_audit_event_has_no_updated_at() -> None:
    """Append-only — never mutated; should not carry an updated_at column."""
    audit = Base.metadata.tables["audit_event"]
    assert "updated_at" not in audit.columns
    assert "at" in audit.columns


def test_invoice_status_enum_covers_design_states() -> None:
    """All seven invoice states from design §4.4 must be present."""
    from app.invoices.models import InvoiceStatus

    expected = {
        "open", "partial", "paid", "overdue",
        "on_pay_plan", "defaulted", "written_off",
    }
    assert {s.value for s in InvoiceStatus} == expected


def test_payment_channels_match_design() -> None:
    from app.payments.models import PaymentChannel

    assert {c.value for c in PaymentChannel} == {"mpesa_stk", "mpesa_c2b", "cash", "bank"}


def test_user_role_values() -> None:
    from app.users.models import UserRole

    assert {r.value for r in UserRole} == {"landlord", "tenant", "admin"}
