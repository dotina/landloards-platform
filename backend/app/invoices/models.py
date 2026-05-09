"""Invoice model + status enum."""
from __future__ import annotations

import enum
import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, KESAmount, TimestampMixin


class InvoiceStatus(enum.StrEnum):
    OPEN = "open"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"
    ON_PAY_PLAN = "on_pay_plan"
    DEFAULTED = "defaulted"
    WRITTEN_OFF = "written_off"


class Invoice(IdMixin, TimestampMixin, Base):
    """Rent obligation for one billing period."""

    __tablename__ = "invoices"
    __table_args__ = (
        # Generator must be idempotent: only one invoice per (lease, period_start).
        UniqueConstraint("lease_id", "period_start", name="uq_invoices_lease_period"),
    )

    lease_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("leases.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[KESAmount]
    late_fee_accrued: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False, default=Decimal("0")
    )
    status: Mapped[InvoiceStatus] = mapped_column(
        SAEnum(
            InvoiceStatus,
            name="invoice_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=InvoiceStatus.OPEN,
        index=True,
    )
    write_off_reason: Mapped[str | None]
