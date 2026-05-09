"""Tenants + KYC business logic."""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.core.storage import remove_object
from app.tenants.models import KycStatus, Tenant
from app.tenants.schemas import KycDecisionRequest, TenantUpdateProfile
from app.users.models import User, UserRole


class TenantError(Exception):
    pass


class TenantNotFound(TenantError):
    pass


class KycInvalidState(TenantError):
    """Cannot transition KYC from current state to requested state."""


async def get_tenant_by_user_id(
    db: AsyncSession, *, user_id: uuid.UUID
) -> Optional[Tenant]:
    stmt = select(Tenant).where(Tenant.user_id == user_id)
    return (await db.execute(stmt)).scalar_one_or_none()


async def list_tenants(db: AsyncSession) -> Sequence[tuple[Tenant, User]]:
    """Returns (tenant, user) pairs sorted by user.name."""
    stmt = (
        select(Tenant, User)
        .join(User, Tenant.user_id == User.id)
        .where(User.role == UserRole.TENANT)
        .order_by(User.name)
    )
    return [(t, u) for t, u in (await db.execute(stmt)).all()]


async def get_tenant(
    db: AsyncSession, *, tenant_id: uuid.UUID
) -> tuple[Tenant, User]:
    stmt = (
        select(Tenant, User)
        .join(User, Tenant.user_id == User.id)
        .where(Tenant.id == tenant_id)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise TenantNotFound()
    return row[0], row[1]


async def update_tenant_profile(
    db: AsyncSession, *, tenant: Tenant, body: TenantUpdateProfile
) -> Tenant:
    if body.employer is not None:
        tenant.employer = body.employer
    if body.next_of_kin is not None:
        tenant.next_of_kin = body.next_of_kin.model_dump()
    await db.flush()
    return tenant


async def attach_kyc_doc(
    db: AsyncSession, *, tenant: Tenant, key: str
) -> Tenant:
    """Replace any prior KYC doc with the new MinIO key.

    Returns tenant with `id_doc_url=key` and `kyc_status` reset to PENDING
    (any prior approval/rejection is invalidated by re-uploading).
    """
    if tenant.id_doc_url and tenant.id_doc_url != key:
        try:
            remove_object(key=tenant.id_doc_url)
        except Exception:  # noqa: BLE001
            # The orphan blob is acceptable; better than failing the upload.
            pass
    tenant.id_doc_url = key
    tenant.kyc_status = KycStatus.PENDING
    tenant.kyc_rejected_reason = None
    await db.flush()
    return tenant


async def decide_kyc(
    db: AsyncSession,
    *,
    actor: User,
    tenant_id: uuid.UUID,
    body: KycDecisionRequest,
) -> Tenant:
    tenant, _user = await get_tenant(db, tenant_id=tenant_id)

    if tenant.id_doc_url is None and body.action == "approve":
        raise KycInvalidState("cannot approve without an uploaded ID doc")

    if body.action == "approve":
        tenant.kyc_status = KycStatus.APPROVED
        tenant.kyc_rejected_reason = None
    else:
        tenant.kyc_status = KycStatus.REJECTED
        tenant.kyc_rejected_reason = body.reason or "rejected"

    await audit.log(
        db,
        actor_id=actor.id,
        action=f"kyc.{body.action}",
        entity_type="tenant",
        entity_id=tenant.id,
        meta={"reason": body.reason} if body.reason else None,
    )
    await db.flush()
    return tenant
