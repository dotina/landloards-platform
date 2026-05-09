"""Pure-unit tests for lease schemas + invariant smoke."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.models import Base
import app.core.all_models  # noqa: F401
from app.leases.schemas import LateFeeRule, LeaseCreate


def test_late_fee_rule_flat_ok() -> None:
    LateFeeRule(type="flat", value=Decimal("500"), cadence="once", grace_days=3, cap_months=2)


def test_late_fee_rule_percent_capped_at_100() -> None:
    with pytest.raises(ValidationError):
        LateFeeRule(
            type="percent", value=Decimal("250"), cadence="monthly", grace_days=0, cap_months=1
        )


def test_late_fee_rule_grace_days_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        LateFeeRule(
            type="flat", value=Decimal("0"), cadence="once", grace_days=-1, cap_months=1
        )


def test_late_fee_rule_value_cannot_be_negative() -> None:
    with pytest.raises(ValidationError):
        LateFeeRule(
            type="flat", value=Decimal("-1"), cadence="once", grace_days=0, cap_months=1
        )


def test_lease_create_end_must_be_after_start() -> None:
    rule = LateFeeRule(
        type="flat", value=Decimal("0"), cadence="once", grace_days=0, cap_months=1
    )
    with pytest.raises(ValidationError):
        LeaseCreate(
            unit_id="00000000-0000-0000-0000-000000000001",
            tenant_id="00000000-0000-0000-0000-000000000002",
            start_date=date(2026, 1, 31),
            end_date=date(2026, 1, 1),
            rent_amount=Decimal("25000"),
            deposit_amount=Decimal("25000"),
            late_fee_rule=rule,
        )


def test_lease_table_has_partial_unique_active_index() -> None:
    """Calendar invariant: only one ACTIVE lease per unit at a time."""
    leases = Base.metadata.tables["leases"]
    idx = next((i for i in leases.indexes if i.name == "uq_leases_unit_active"), None)
    assert idx is not None
    assert idx.unique is True
    where = idx.dialect_options["postgresql"]["where"]
    assert where is not None
    # Compile to SQL to confirm the predicate.
    rendered = str(where.compile(compile_kwargs={"literal_binds": True})) if hasattr(where, "compile") else str(where)
    assert "active" in rendered


def test_app_router_has_lease_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/leases" in paths
    assert "/leases/{lease_id}" in paths
    assert "/leases/{lease_id}/end" in paths
