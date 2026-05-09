"""Late-fee accrual: pure-function tests."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from app.jobs.late_fee import (
    LateFeeParams,
    compute_target_accrued,
    periods_past_grace,
)


def _flat(value: Decimal, cadence: str, *, grace: int = 0, cap: int = 1) -> LateFeeParams:
    return LateFeeParams(
        type_="flat", value=value, cadence=cadence, grace_days=grace, cap_months=cap
    )


def _pct(pct: Decimal, cadence: str, *, grace: int = 0, cap: int = 1) -> LateFeeParams:
    return LateFeeParams(
        type_="percent", value=pct, cadence=cadence, grace_days=grace, cap_months=cap
    )


def test_no_accrual_before_grace() -> None:
    """Boundary == due_date + grace_days. today < boundary ⇒ no accrual."""
    p = _flat(Decimal("500"), "daily", grace=3)
    # 2026-05-03 is before 2026-05-04 (boundary) → 0 periods.
    assert periods_past_grace(date(2026, 5, 3), date(2026, 5, 1), p) == 0
    assert compute_target_accrued(
        rent_amount=Decimal("25000"),
        today=date(2026, 5, 3),
        due_date=date(2026, 5, 1),
        params=p,
    ) == Decimal("0")


def test_flat_once_at_grace_boundary() -> None:
    p = _flat(Decimal("500"), "once", grace=3, cap=12)
    val = compute_target_accrued(
        rent_amount=Decimal("25000"),
        today=date(2026, 5, 4),  # due 2026-05-01 + 3d grace
        due_date=date(2026, 5, 1),
        params=p,
    )
    assert val == Decimal("500.00")


def test_flat_daily_accrues_per_day_past_grace() -> None:
    p = _flat(Decimal("100"), "daily", grace=0, cap=12)
    val = compute_target_accrued(
        rent_amount=Decimal("25000"),
        today=date(2026, 5, 11),
        due_date=date(2026, 5, 1),
        params=p,
    )
    # 11 days past grace boundary == days 1..11 inclusive == 11 periods.
    assert val == Decimal("1100.00")


def test_flat_monthly_accrues_per_30_days() -> None:
    p = _flat(Decimal("1000"), "monthly", grace=0, cap=12)
    # 60 days past due → 3 periods (1 + 60//30).
    val = compute_target_accrued(
        rent_amount=Decimal("25000"),
        today=date(2026, 7, 1),
        due_date=date(2026, 5, 2),
        params=p,
    )
    assert val == Decimal("3000.00")


def test_percent_daily_accrues_relative_to_rent() -> None:
    p = _pct(Decimal("1"), "daily", grace=0, cap=12)
    val = compute_target_accrued(
        rent_amount=Decimal("10000"),
        today=date(2026, 5, 11),  # 11 days past due
        due_date=date(2026, 5, 1),
        params=p,
    )
    # 1% of 10000 = 100 per day × 11 = 1100
    assert val == Decimal("1100.00")


def test_cap_at_rent_times_cap_months() -> None:
    p = _flat(Decimal("100000"), "daily", grace=0, cap=2)
    val = compute_target_accrued(
        rent_amount=Decimal("25000"),
        today=date(2026, 5, 11),
        due_date=date(2026, 5, 1),
        params=p,
    )
    # Raw would be 11×100000 = 1.1M, but cap = 25000×2 = 50000.
    assert val == Decimal("50000.00")


def test_from_jsonb_supports_camel_and_snake() -> None:
    a = LateFeeParams.from_jsonb(
        {"type": "flat", "value": "500", "cadence": "once", "graceDays": 3, "capMonths": 2}
    )
    b = LateFeeParams.from_jsonb(
        {"type": "flat", "value": "500", "cadence": "once", "grace_days": 3, "cap_months": 2}
    )
    assert a == b
