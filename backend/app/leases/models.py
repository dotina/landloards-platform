"""Lease model: tenancy agreement linking unit ↔ tenant."""
from __future__ import annotations

import enum
import uuid
from datetime import date
from typing import Any

from sqlalchemy import Date, ForeignKey, Index, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, KESAmount, TimestampMixin


class LeaseStatus(enum.StrEnum):
    ACTIVE = "active"
    ENDED = "ended"
    TERMINATED = "terminated"


class Lease(IdMixin, TimestampMixin, Base):
    """Tenancy agreement.

    `late_fee_rule` jsonb shape:
        {
          "type": "flat" | "percent",
          "value": number,
          "cadence": "once" | "daily" | "monthly",
          "graceDays": int,
          "capMonths": int
        }
    Validation lives in `app.leases.schemas` (Pydantic).
    """

    __tablename__ = "leases"
    __table_args__ = (
        Index("ix_leases_unit_status", "unit_id", "status"),
        Index("ix_leases_tenant_status", "tenant_id", "status"),
        # Calendar invariant from design §5: at most one ACTIVE lease per unit.
        Index(
            "uq_leases_unit_active",
            "unit_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
        ),
    )

    unit_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("units.id", ondelete="RESTRICT"),
        nullable=False,
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date)
    rent_amount: Mapped[KESAmount]
    deposit_amount: Mapped[KESAmount]
    late_fee_rule: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[LeaseStatus] = mapped_column(
        SAEnum(LeaseStatus, name="lease_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=LeaseStatus.ACTIVE,
    )
    end_reason: Mapped[str | None]
