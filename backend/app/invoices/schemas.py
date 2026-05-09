"""Pydantic schemas for invoices."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class InvoiceOut(BaseModel):
    id: uuid.UUID
    lease_id: uuid.UUID
    period_start: date
    period_end: date
    due_date: date
    amount: Decimal
    late_fee_accrued: Decimal
    status: str
    write_off_reason: str | None = None

    model_config = ConfigDict(from_attributes=True)


class InvoiceWriteOffRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
