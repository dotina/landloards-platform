"""HTTP routes — admin notification log."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord, require_tenant
from app.notifications import service
from app.notifications.models import NotificationChannel, NotificationStatus
from app.users.models import User


class NotificationLogOut(BaseModel):
    id: uuid.UUID
    recipient_user_id: uuid.UUID
    channel: str
    template: str
    body: str
    provider_message_id: str | None
    status: str
    error: str | None
    created_at: object | None = None

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


@router.get("", response_model=list[NotificationLogOut])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
    recipient_id: uuid.UUID | None = None,
    channel: NotificationChannel | None = Query(default=None),
    status_: NotificationStatus | None = Query(default=None, alias="status"),
) -> list[NotificationLogOut]:
    rows = await service.list_for_admin(
        db, recipient_id=recipient_id, channel=channel, status_=status_
    )
    return [NotificationLogOut.model_validate(r) for r in rows]


tenant_router = APIRouter(prefix="/tenant/notifications", tags=["tenant-notifications"])


@tenant_router.get("", response_model=list[NotificationLogOut])
async def list_my_notifications(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> list[NotificationLogOut]:
    rows = await service.list_for_admin(db, recipient_id=user.id)
    return [NotificationLogOut.model_validate(r) for r in rows]
