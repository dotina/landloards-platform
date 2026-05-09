"""NotificationLog: every SMS/email — audit + delivery trail."""
from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, TimestampMixin


class NotificationChannel(enum.StrEnum):
    SMS = "sms"
    EMAIL = "email"


class NotificationStatus(enum.StrEnum):
    QUEUED = "queued"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"


class NotificationLog(IdMixin, TimestampMixin, Base):
    """Audit + delivery trail row per outbound message."""

    __tablename__ = "notification_log"

    recipient_user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    channel: Mapped[NotificationChannel] = mapped_column(
        SAEnum(
            NotificationChannel,
            name="notification_channel",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
    )
    template: Mapped[str] = mapped_column(String(64), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    provider_message_id: Mapped[str | None] = mapped_column(String(128))
    status: Mapped[NotificationStatus] = mapped_column(
        SAEnum(
            NotificationStatus,
            name="notification_status",
            values_callable=lambda e: [m.value for m in e],
        ),
        nullable=False,
        default=NotificationStatus.QUEUED,
        index=True,
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(Text)
