"""Audit logging helpers.

Always call from inside an open transaction; the caller commits.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.audit.models import AuditEvent


async def log(
    db: AsyncSession,
    *,
    actor_id: uuid.UUID | None,
    action: str,
    entity_type: str,
    entity_id: uuid.UUID | None = None,
    meta: dict[str, Any] | None = None,
) -> AuditEvent:
    evt = AuditEvent(
        actor_id=actor_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        meta=meta,
        at=datetime.now(tz=UTC),
    )
    db.add(evt)
    await db.flush()
    return evt
