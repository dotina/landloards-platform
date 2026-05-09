"""Compliance endpoints — data export and privacy notice.

Per design §8 (privacy + retention) and the Phase 16 cutover gate. The
data-export endpoint returns a JSON document that any user (landlord
*or* tenant) can request for themselves, satisfying GDPR-style
right-to-access while keeping the surface minimal for MVP.
"""
from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import get_current_user
from app.invoices.models import Invoice
from app.leases.models import Lease
from app.notifications.models import NotificationLog
from app.payments.models import Payment
from app.tenants.models import Tenant
from app.users.models import User

router = APIRouter(prefix="/me", tags=["compliance"])


def _serialize(obj: Any) -> Any:
    if isinstance(obj, datetime):
        return obj.astimezone(UTC).isoformat()
    if hasattr(obj, "value"):  # enum
        return obj.value
    return str(obj)


def _row_to_dict(row: Any, *, exclude: set[str] | None = None) -> dict[str, Any]:
    d: dict[str, Any] = {}
    for col in row.__table__.columns:
        if exclude and col.name in exclude:
            continue
        v = getattr(row, col.name)
        if isinstance(v, (str, int, float, bool, type(None))):
            d[col.name] = v
        else:
            d[col.name] = _serialize(v)
    return d


@router.get("/export")
async def me_export(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    payload: dict[str, Any] = {
        "exported_at": datetime.now(tz=UTC).isoformat(),
        "user": _row_to_dict(
            user, exclude={"hashed_password", "id_number_encrypted", "kra_pin_encrypted"}
        ),
    }

    if user.role.value == "tenant":
        tenant = (
            await db.execute(select(Tenant).where(Tenant.user_id == user.id))
        ).scalar_one_or_none()
        if tenant is not None:
            payload["tenant_profile"] = _row_to_dict(tenant)
            tenant_id = tenant.id

            leases = (
                await db.execute(select(Lease).where(Lease.tenant_id == tenant_id))
            ).scalars().all()
            payload["leases"] = [_row_to_dict(lease) for lease in leases]

            lease_ids = [lease.id for lease in leases]
            invoices = (
                await db.execute(select(Invoice).where(Invoice.lease_id.in_(lease_ids)))
            ).scalars().all() if lease_ids else []
            payload["invoices"] = [_row_to_dict(i) for i in invoices]

            payments = (
                await db.execute(select(Payment).where(Payment.tenant_id == tenant_id))
            ).scalars().all()
            payload["payments"] = [_row_to_dict(p) for p in payments]

    notifications = (
        await db.execute(
            select(NotificationLog).where(NotificationLog.recipient_user_id == user.id)
        )
    ).scalars().all()
    payload["notifications"] = [_row_to_dict(n) for n in notifications]

    body = json.dumps(payload, indent=2, default=_serialize)
    return Response(
        content=body,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="landloads-export-{user.id}.json"',
        },
    )


@router.get("/privacy-notice")
async def privacy_notice() -> dict[str, Any]:
    return {
        "version": "2026-05-09",
        "data_we_collect": [
            "name, phone, email",
            "Kenyan ID number and KRA PIN (encrypted at rest with pgcrypto)",
            "M-Pesa transaction receipts and amounts",
            "lease, invoice, payment, and audit history",
        ],
        "purpose": [
            "operate your tenancy with your landlord",
            "send rent reminders, OTPs, and payment receipts",
            "demonstrate compliance with KRA and Data Protection Act",
        ],
        "retention": (
            "We keep your records for 7 years after your last lease ends, "
            "as required by Kenyan tax + tenancy regulations. "
            "You can request a deletion review by emailing privacy@landloads."
        ),
        "your_rights": [
            "GET /api/me/export — download your data as JSON",
            "POST /api/me/deletion-request — schedule deletion after the 7-year clock",
            "Email privacy@landloads to dispute or correct any record.",
        ],
    }
