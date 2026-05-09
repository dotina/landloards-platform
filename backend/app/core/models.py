"""SQLAlchemy declarative base, mixins, and shared types."""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Annotated

from sqlalchemy import DateTime, Numeric, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Project-wide declarative base."""


# Numeric(12, 2) — Kenyan shillings with cents; max 9 999 999 999.99 KES.
KESAmount = Annotated[Decimal, mapped_column(Numeric(12, 2))]


class IdMixin:
    """UUID primary key generated client-side for predictability."""

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class TimestampMixin:
    """`created_at` and `updated_at` populated by the DB."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
