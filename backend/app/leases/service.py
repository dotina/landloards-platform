"""Lease lifecycle service."""
from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.audit import service as audit
from app.leases.models import Lease, LeaseStatus
from app.leases.schemas import LeaseCreate, LeaseEnd
from app.properties.models import Property, Unit, UnitStatus
from app.tenants.models import Tenant
from app.users.models import User, UserRole


class LeaseError(Exception):
    pass


class LeaseNotFound(LeaseError):
    pass


class LeaseConflict(LeaseError):
    """A unit already has an active lease."""


class TenantNotEligible(LeaseError):
    """Tenant must exist and be KYC-verified before being assigned a lease."""


async def list_leases(
    db: AsyncSession,
    *,
    landlord: User,
    status_: LeaseStatus | None = None,
    unit_id: uuid.UUID | None = None,
    tenant_id: uuid.UUID | None = None,
) -> Sequence[Lease]:
    stmt = (
        select(Lease)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .where(Property.landlord_id == landlord.id)
        .order_by(Lease.start_date.desc())
    )
    if status_ is not None:
        stmt = stmt.where(Lease.status == status_)
    if unit_id is not None:
        stmt = stmt.where(Lease.unit_id == unit_id)
    if tenant_id is not None:
        stmt = stmt.where(Lease.tenant_id == tenant_id)
    return (await db.execute(stmt)).scalars().all()


async def _ensure_unit_belongs_to_landlord(
    db: AsyncSession, *, landlord: User, unit_id: uuid.UUID
) -> Unit:
    stmt = (
        select(Unit)
        .join(Property, Property.id == Unit.property_id)
        .where(Unit.id == unit_id, Property.landlord_id == landlord.id)
    )
    unit = (await db.execute(stmt)).scalar_one_or_none()
    if unit is None:
        raise LeaseNotFound()
    return unit


async def _ensure_tenant_exists(db: AsyncSession, *, tenant_id: uuid.UUID) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise TenantNotEligible("tenant not found")
    return tenant


async def create_lease(
    db: AsyncSession,
    *,
    landlord: User,
    body: LeaseCreate,
) -> Lease:
    if landlord.role not in (UserRole.LANDLORD, UserRole.ADMIN):
        raise LeaseError("only landlord may create leases")

    unit = await _ensure_unit_belongs_to_landlord(db, landlord=landlord, unit_id=body.unit_id)
    await _ensure_tenant_exists(db, tenant_id=body.tenant_id)

    lease = Lease(
        unit_id=body.unit_id,
        tenant_id=body.tenant_id,
        start_date=body.start_date,
        end_date=body.end_date,
        rent_amount=body.rent_amount,
        deposit_amount=body.deposit_amount,
        late_fee_rule=body.late_fee_rule.model_dump(mode="json"),
        status=LeaseStatus.ACTIVE,
    )
    db.add(lease)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise LeaseConflict("unit already has an active lease") from exc

    unit.status = UnitStatus.OCCUPIED
    await db.flush()

    await audit.log(
        db,
        actor_id=landlord.id,
        action="lease.create",
        entity_type="lease",
        entity_id=lease.id,
        meta={"unit_id": str(body.unit_id), "tenant_id": str(body.tenant_id)},
    )
    return lease


async def get_lease_owned(
    db: AsyncSession, *, landlord: User, lease_id: uuid.UUID
) -> Lease:
    stmt = (
        select(Lease)
        .join(Unit, Unit.id == Lease.unit_id)
        .join(Property, Property.id == Unit.property_id)
        .where(Lease.id == lease_id, Property.landlord_id == landlord.id)
    )
    lease = (await db.execute(stmt)).scalar_one_or_none()
    if lease is None:
        raise LeaseNotFound()
    return lease


async def end_lease(
    db: AsyncSession,
    *,
    landlord: User,
    lease_id: uuid.UUID,
    body: LeaseEnd,
) -> Lease:
    lease = await get_lease_owned(db, landlord=landlord, lease_id=lease_id)
    if lease.status != LeaseStatus.ACTIVE:
        raise LeaseError("only active leases can be ended")

    lease.status = LeaseStatus.ENDED
    lease.end_date = body.end_date
    lease.end_reason = body.reason

    # Cascade unit back to vacant *only* if no other active lease exists on the unit.
    other = await db.execute(
        select(Lease).where(
            Lease.unit_id == lease.unit_id,
            Lease.status == LeaseStatus.ACTIVE,
            Lease.id != lease.id,
        )
    )
    if other.scalar_one_or_none() is None:
        unit = await db.get(Unit, lease.unit_id)
        if unit is not None:
            unit.status = UnitStatus.VACANT

    await audit.log(
        db,
        actor_id=landlord.id,
        action="lease.end",
        entity_type="lease",
        entity_id=lease.id,
        meta={"end_date": body.end_date.isoformat(), "reason": body.reason},
    )
    await db.flush()
    return lease
