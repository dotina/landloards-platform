"""PaymentPlan: tenant-proposed deferred schedule."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, TimestampMixin


class PaymentPlanStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    DEFAULTED = "defaulted"


class PaymentPlan(IdMixin, TimestampMixin, Base):
    """Tenant-proposed deferred schedule.

    `schedule` jsonb shape:
        [{ "date": "YYYY-MM-DD", "amount": Decimal, "paid_payment_id": uuid|null }]
    """

    __tablename__ = "payment_plans"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    approved_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT")
    )
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    schedule: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    status: Mapped[PaymentPlanStatus] = mapped_column(
        SAEnum(
            PaymentPlanStatus,
            name="payment_plan_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=PaymentPlanStatus.PENDING,
        index=True,
    )
    rejection_reason: Mapped[Optional[str]]
