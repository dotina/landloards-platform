"""HTTP routes — admin notification log."""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord
from app.notifications import service
from app.notifications.models import NotificationChannel, NotificationStatus
from app.users.models import User


class NotificationLogOut(BaseModel):
    id: uuid.UUID
    recipient_user_id: uuid.UUID
    channel: str
    template: str
    body: str
    provider_message_id: Optional[str]
    status: str
    error: Optional[str]

    model_config = ConfigDict(from_attributes=True)


router = APIRouter(prefix="/admin/notifications", tags=["admin-notifications"])


@router.get("", response_model=list[NotificationLogOut])
async def list_notifications(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],  # noqa: ARG001
    recipient_id: Optional[uuid.UUID] = None,
    channel: Optional[NotificationChannel] = Query(default=None),
    status_: Optional[NotificationStatus] = Query(default=None, alias="status"),
) -> list[NotificationLogOut]:
    rows = await service.list_for_admin(
        db, recipient_id=recipient_id, channel=channel, status_=status_
    )
    return [NotificationLogOut.model_validate(r) for r in rows]
