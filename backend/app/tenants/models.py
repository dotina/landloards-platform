"""Tenant model + KYC status."""
from __future__ import annotations

import enum
import uuid
from typing import Any, Optional

from sqlalchemy import Enum as SAEnum, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, TimestampMixin


class KycStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Tenant(IdMixin, TimestampMixin, Base):
    """Tenant profile linked 1:1 with a User row."""

    __tablename__ = "tenants"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    id_doc_url: Mapped[Optional[str]] = mapped_column(String(500))
    employer: Mapped[Optional[str]] = mapped_column(String(255))
    next_of_kin: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    kyc_status: Mapped[KycStatus] = mapped_column(
        SAEnum(KycStatus, name="kyc_status", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=KycStatus.PENDING,
    )
    kyc_rejected_reason: Mapped[Optional[str]] = mapped_column(String(500))
