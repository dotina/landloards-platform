"""Pydantic schemas for leases.

Includes the strict ``LateFeeRule`` validator from design §3.1.
"""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class LateFeeRule(BaseModel):
    """Per-lease late-fee accrual rule.

    Phase 10 cron consumes this; Phase 6 must respect ``on_pay_plan``
    invoices skipping accrual entirely.
    """

    type: Literal["flat", "percent"]
    value: Decimal = Field(ge=0)
    cadence: Literal["once", "daily", "monthly"]
    grace_days: int = Field(ge=0, le=365)
    cap_months: int = Field(ge=1, le=24)

    @field_validator("value")
    @classmethod
    def percent_under_100(cls, v: Decimal, info) -> Decimal:  # type: ignore[no-untyped-def]
        type_ = info.data.get("type")
        if type_ == "percent" and v > Decimal("100"):
            raise ValueError("percent rule must be <= 100")
        return v


class LeaseCreate(BaseModel):
    unit_id: uuid.UUID
    tenant_id: uuid.UUID
    start_date: date
    end_date: Optional[date] = None
    rent_amount: Decimal = Field(ge=0)
    deposit_amount: Decimal = Field(ge=0)
    late_fee_rule: LateFeeRule

    @model_validator(mode="after")
    def _end_after_start(self) -> "LeaseCreate":
        if self.end_date is not None and self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaseEnd(BaseModel):
    end_date: date
    reason: str = Field(min_length=1, max_length=500)


class LeaseOut(BaseModel):
    id: uuid.UUID
    unit_id: uuid.UUID
    tenant_id: uuid.UUID
    start_date: date
    end_date: Optional[date]
    rent_amount: Decimal
    deposit_amount: Decimal
    late_fee_rule: dict  # raw jsonb for now; clients re-validate via LateFeeRule
    status: str
    end_reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)
