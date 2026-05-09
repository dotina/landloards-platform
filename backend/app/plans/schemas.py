"""Pydantic schemas for payment plans."""
from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class Installment(BaseModel):
    date: date  # noqa: A003 (intentional shadow for shape)
    amount: Decimal = Field(gt=0)
    paid_payment_id: Optional[uuid.UUID] = None


class PlanRequest(BaseModel):
    invoice_id: uuid.UUID
    schedule: list[Installment] = Field(min_length=1, max_length=12)

    @field_validator("schedule")
    @classmethod
    def installments_in_order(cls, v: list[Installment]) -> list[Installment]:
        for i in range(1, len(v)):
            if v[i].date <= v[i - 1].date:
                raise ValueError("installment dates must be strictly increasing")
        return v


class PlanCounter(BaseModel):
    schedule: list[Installment] = Field(min_length=1, max_length=12)


class PlanDecision(BaseModel):
    action: Literal["approve", "reject", "counter"]
    reason: Optional[str] = Field(default=None, max_length=500)
    counter_schedule: Optional[list[Installment]] = None

    @model_validator(mode="after")
    def _counter_pairing(self) -> "PlanDecision":
        if self.action == "counter" and not self.counter_schedule:
            raise ValueError("counter requires counter_schedule")
        if self.action != "counter" and self.counter_schedule:
            raise ValueError("counter_schedule only allowed when action='counter'")
        return self


class PlanOut(BaseModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    status: str
    schedule: list[dict]
    rejection_reason: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
