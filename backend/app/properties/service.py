"""Business logic for Properties + Units."""
from __future__ import annotations

import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.leases.models import Lease, LeaseStatus
from app.properties.models import Property, Unit, UnitStatus
from app.properties.schemas import PropertyCreate, PropertyUpdate, UnitCreate, UnitUpdate
from app.users.models import User


class PropertyError(Exception):
    """Base."""


class PropertyNotFound(PropertyError):
    pass


class UnitNotFound(PropertyError):
    pass


class UnitInUse(PropertyError):
    """Cannot delete a unit with active leases."""


# ─── Properties ──────────────────────────────────────────────────────
async def list_properties(db: AsyncSession, *, landlord: User) -> Sequence[Property]:
    stmt = select(Property).where(Property.landlord_id == landlord.id).order_by(Property.name)
    return (await db.execute(stmt)).scalars().all()


async def create_property(
    db: AsyncSession, *, landlord: User, body: PropertyCreate
) -> Property:
    p = Property(
        landlord_id=landlord.id,
        name=body.name,
        address=body.address,
        lat=body.lat,
        lng=body.lng,
    )
    db.add(p)
    await db.flush()
    return p


async def get_property_owned(
    db: AsyncSession, *, landlord: User, property_id: uuid.UUID
) -> Property:
    p = await db.get(Property, property_id)
    if p is None or p.landlord_id != landlord.id:
        # 404 (not 403) — never leak the existence of others' rows.
        raise PropertyNotFound()
    return p


async def update_property(
    db: AsyncSession, *, landlord: User, property_id: uuid.UUID, body: PropertyUpdate
) -> Property:
    p = await get_property_owned(db, landlord=landlord, property_id=property_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.flush()
    return p


async def delete_property(
    db: AsyncSession, *, landlord: User, property_id: uuid.UUID
) -> None:
    p = await get_property_owned(db, landlord=landlord, property_id=property_id)
    await db.delete(p)
    await db.flush()


async def set_property_photo(
    db: AsyncSession, *, landlord: User, property_id: uuid.UUID, photo_url: str
) -> Property:
    p = await get_property_owned(db, landlord=landlord, property_id=property_id)
    p.photo_url = photo_url
    await db.flush()
    return p


# ─── Units ───────────────────────────────────────────────────────────
async def list_units(
    db: AsyncSession, *, landlord: User, property_id: uuid.UUID
) -> Sequence[Unit]:
    await get_property_owned(db, landlord=landlord, property_id=property_id)
    stmt = select(Unit).where(Unit.property_id == property_id).order_by(Unit.label)
    return (await db.execute(stmt)).scalars().all()


async def create_unit(
    db: AsyncSession, *, landlord: User, property_id: uuid.UUID, body: UnitCreate
) -> Unit:
    await get_property_owned(db, landlord=landlord, property_id=property_id)
    u = Unit(
        property_id=property_id,
        label=body.label,
        bedrooms=body.bedrooms,
        rent_amount=body.rent_amount,
        deposit_amount=body.deposit_amount,
        due_day_of_month=body.due_day_of_month,
        status=UnitStatus.VACANT,
    )
    db.add(u)
    await db.flush()
    return u


async def get_unit_owned(
    db: AsyncSession, *, landlord: User, unit_id: uuid.UUID
) -> Unit:
    u = await db.get(Unit, unit_id)
    if u is None:
        raise UnitNotFound()
    parent = await db.get(Property, u.property_id)
    if parent is None or parent.landlord_id != landlord.id:
        raise UnitNotFound()
    return u


async def update_unit(
    db: AsyncSession, *, landlord: User, unit_id: uuid.UUID, body: UnitUpdate
) -> Unit:
    u = await get_unit_owned(db, landlord=landlord, unit_id=unit_id)
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(u, k, v)
    await db.flush()
    return u


async def delete_unit(
    db: AsyncSession, *, landlord: User, unit_id: uuid.UUID
) -> None:
    u = await get_unit_owned(db, landlord=landlord, unit_id=unit_id)
    # Block delete if any active lease references this unit (Phase 5 model).
    stmt = select(Lease).where(
        Lease.unit_id == u.id, Lease.status == LeaseStatus.ACTIVE
    ).limit(1)
    if (await db.execute(stmt)).scalar_one_or_none() is not None:
        raise UnitInUse("unit has an active lease")
    await db.delete(u)
    await db.flush()
