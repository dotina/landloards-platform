"""Pydantic schemas for payments."""
from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StkInitiateRequest(BaseModel):
    invoice_id: uuid.UUID
    amount: Decimal = Field(gt=0)
    phone: str = Field(min_length=10, max_length=15, description="2547XXXXXXXX format")

    @field_validator("phone")
    @classmethod
    def normalise_phone(cls, v: str) -> str:
        v = v.strip().lstrip("+")
        if v.startswith("0"):
            v = "254" + v[1:]
        if not (v.startswith("254") and v[3:].isdigit() and len(v) == 12):
            raise ValueError("phone must be 254XXXXXXXXX")
        return v


class StkInitiateResponse(BaseModel):
    payment_id: uuid.UUID
    checkout_request_id: str
    status: str


class PaymentOut(BaseModel):
    id: uuid.UUID
    invoice_id: Optional[uuid.UUID]
    tenant_id: uuid.UUID
    amount: Decimal
    channel: str
    status: str
    mpesa_receipt: Optional[str]
    checkout_request_id: Optional[str]
    failure_reason: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class StkCallbackBody(BaseModel):
    """Daraja STK callback envelope (Body.stkCallback)."""

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    Body: dict[str, Any]
