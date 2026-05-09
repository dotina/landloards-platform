"""AuditEvent: append-only log of admin actions.

Postgres role grants are tightened in the migration so the app role
cannot UPDATE or DELETE — see design §3.2.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin


class AuditEvent(IdMixin, Base):
    """Append-only audit row.

    No `updated_at` — these rows must never be updated.
    """

    __tablename__ = "audit_event"

    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        index=True,
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[Optional[uuid.UUID]] = mapped_column(PG_UUID(as_uuid=True), index=True)
    meta: Mapped[Optional[dict[str, Any]]] = mapped_column(JSONB)
    at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
