"""Payment model + idempotency-keyed indexes."""
from __future__ import annotations

import enum
import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, KESAmount, TimestampMixin


class PaymentChannel(enum.StrEnum):
    MPESA_STK = "mpesa_stk"
    MPESA_C2B = "mpesa_c2b"
    CASH = "cash"
    BANK = "bank"


class PaymentStatus(enum.StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    FAILED = "failed"
    REVERSED = "reversed"


class Payment(IdMixin, TimestampMixin, Base):
    """Money received."""

    __tablename__ = "payments"
    __table_args__ = (
        # Design §3.2 invariants — partial unique indexes for idempotency.
        Index(
            "uq_payments_channel_mpesa_receipt",
            "channel",
            "mpesa_receipt",
            unique=True,
            postgresql_where=text("mpesa_receipt IS NOT NULL"),
        ),
        Index(
            "uq_payments_checkout_request_id",
            "checkout_request_id",
            unique=True,
            postgresql_where=text("checkout_request_id IS NOT NULL"),
        ),
        Index("ix_payments_invoice_status", "invoice_id", "status"),
    )

    invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    amount: Mapped[KESAmount]
    channel: Mapped[PaymentChannel] = mapped_column(
        SAEnum(
            PaymentChannel,
            name="payment_channel",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    mpesa_receipt: Mapped[str | None] = mapped_column(String(64))
    checkout_request_id: Mapped[str | None] = mapped_column(String(64))
    raw_callback: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(
            PaymentStatus,
            name="payment_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    failure_reason: Mapped[str | None] = mapped_column(String(500))
