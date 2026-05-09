"""C2B unmatched-payment model.

When a Paybill receipt arrives with an unrecognised account reference
(no User has that ``tenant_code``) we park the raw transaction here so a
landlord can manually allocate it later.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, KESAmount, TimestampMixin


class UnmatchedC2B(IdMixin, TimestampMixin, Base):
    """Paybill receipt that doesn't match any tenant_code yet."""

    __tablename__ = "unmatched_c2b"
    __table_args__ = (
        UniqueConstraint("mpesa_receipt", name="uq_unmatched_c2b_receipt"),
    )

    mpesa_receipt: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    bill_ref: Mapped[str | None] = mapped_column(String(64), index=True)
    msisdn: Mapped[str] = mapped_column(String(20), nullable=False)
    amount: Mapped[KESAmount]
    transaction_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    raw: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    is_allocated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    allocated_payment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("payments.id", ondelete="SET NULL")
    )
