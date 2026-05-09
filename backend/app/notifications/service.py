"""Notifications service layer.

Public API (used by every other module that wants to send a message):

    await notifications.send(
        db, recipient=user, channel=NotificationChannel.SMS,
        template="otp", context={"code": "123456", "ttl_min": 10},
    )

The function:
1. Renders the template (raises if missing/typed wrong).
2. Inserts a NotificationLog row with status='queued'.
3. If notifications_enabled is True, dispatches via the chosen provider
   right now and updates the row to sent/failed.
   Otherwise (development), leaves the row queued and logs the body.

Phase 7 keeps it synchronous for simplicity. Phase 10 will move sends
onto an arq job (durable retries on Daraja-style transient failures)
without changing this public surface.
"""
from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.logging import get_logger
from app.notifications import templates
from app.notifications.models import (
    NotificationChannel,
    NotificationLog,
    NotificationStatus,
)
from app.notifications.providers.email_resend import EmailSendError, send_email
from app.notifications.providers.sms_at import SmsSendError, send_sms
from app.users.models import User

log = get_logger("notifications")


class NotificationError(Exception):
    pass


async def send(
    db: AsyncSession,
    *,
    recipient: User,
    channel: NotificationChannel,
    template: str,
    context: dict[str, Any],
) -> NotificationLog:
    if template not in templates.known_templates():
        raise NotificationError(f"unknown template {template!r}")

    body, subject = templates.render(template, context)
    if channel == NotificationChannel.SMS and len(body) > 160:
        log.warning(
            "notification_sms_long",
            template=template,
            length=len(body),
            recipient_user_id=str(recipient.id),
        )

    row = NotificationLog(
        recipient_user_id=recipient.id,
        channel=channel,
        template=template,
        body=body,
        status=NotificationStatus.QUEUED,
    )
    db.add(row)
    await db.flush()

    if not get_settings().notifications_enabled:
        log.info(
            "notification_dev_only",
            template=template,
            channel=channel.value,
            body=body,
            recipient_user_id=str(recipient.id),
        )
        return row

    try:
        if channel == NotificationChannel.SMS:
            sms_result = await send_sms(phone=recipient.phone, body=body)
            row.provider_message_id = sms_result.provider_message_id
        else:
            if not recipient.email:
                raise NotificationError("recipient has no email")
            email_result = await send_email(
                to=recipient.email, subject=subject, text=body
            )
            row.provider_message_id = email_result.provider_message_id
        row.status = NotificationStatus.SENT
        row.sent_at = datetime.now(tz=UTC)
    except (SmsSendError, EmailSendError) as exc:
        row.status = NotificationStatus.FAILED
        row.error = str(exc)[:500]
        log.warning(
            "notification_send_failed",
            template=template,
            channel=channel.value,
            error=row.error,
        )
    await db.flush()
    return row


# ─── Queries (admin) ─────────────────────────────────────────────────
async def list_for_admin(
    db: AsyncSession,
    *,
    recipient_id: uuid.UUID | None = None,
    channel: NotificationChannel | None = None,
    status_: NotificationStatus | None = None,
) -> Sequence[NotificationLog]:
    stmt = select(NotificationLog).order_by(NotificationLog.created_at.desc())
    if recipient_id is not None:
        stmt = stmt.where(NotificationLog.recipient_user_id == recipient_id)
    if channel is not None:
        stmt = stmt.where(NotificationLog.channel == channel)
    if status_ is not None:
        stmt = stmt.where(NotificationLog.status == status_)
    return (await db.execute(stmt)).scalars().all()
