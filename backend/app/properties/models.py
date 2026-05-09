"""Property + Unit models."""
from __future__ import annotations

import enum
import uuid
from typing import Optional

from sqlalchemy import CheckConstraint, Enum as SAEnum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, KESAmount, TimestampMixin


class UnitStatus(str, enum.Enum):
    VACANT = "vacant"
    OCCUPIED = "occupied"


class Property(IdMixin, TimestampMixin, Base):
    """A building or compound owned by a landlord."""

    __tablename__ = "properties"

    landlord_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str] = mapped_column(String(500), nullable=False)
    lat: Mapped[Optional[float]] = mapped_column(Numeric(9, 6))
    lng: Mapped[Optional[float]] = mapped_column(Numeric(9, 6))
    photo_url: Mapped[Optional[str]] = mapped_column(String(500))


class Unit(IdMixin, TimestampMixin, Base):
    """A rentable space inside a property."""

    __tablename__ = "units"
    __table_args__ = (
        CheckConstraint(
            "due_day_of_month >= 1 AND due_day_of_month <= 28",
            name="ck_units_due_day_range",
        ),
    )

    property_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("properties.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    bedrooms: Mapped[int] = mapped_column(nullable=False, default=0)
    rent_amount: Mapped[KESAmount]
    deposit_amount: Mapped[KESAmount]
    due_day_of_month: Mapped[int] = mapped_column(nullable=False, default=1)
    status: Mapped[UnitStatus] = mapped_column(
        SAEnum(UnitStatus, name="unit_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=UnitStatus.VACANT,
    )
