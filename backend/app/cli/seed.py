"""Idempotent dev/demo database seed (landlord, tenant, property, unit, lease).

Run inside the backend container after migrations:
  docker compose exec backend python -m app.cli.seed

See docs/LOCAL.md for default credentials and environment overrides.
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import security
from app.auth.service import DuplicateUser, register_landlord
from app.core.config import get_settings
from app.core.db import get_session_factory
from app.leases.schemas import LateFeeRule, LeaseCreate
from app.leases.service import LeaseConflict, create_lease
from app.leases.models import Lease, LeaseStatus
from app.properties.schemas import PropertyCreate, UnitCreate
from app.properties.service import create_property, create_unit
from app.properties.models import Property, Unit
from app.tenants.models import KycStatus, Tenant
from app.users.models import User, UserRole

# Defaults — override with SEED_* env vars (handy for a deployed demo stack).
_DEFAULT_LANDLORD_PHONE = "+254711000001"
_DEFAULT_TENANT_PHONE = "+254711000002"
_DEFAULT_LANDLORD_PASS = "DevLandlord1"
_DEFAULT_TENANT_PASS = "DevTenant1"
_PROPERTY_NAME = "Seed Demo Property"
_UNIT_LABEL = "A1"


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default).strip()


async def _ensure_landlord(session: AsyncSession) -> User:
    phone = _env("SEED_LANDLORD_PHONE", _DEFAULT_LANDLORD_PHONE)
    password = _env("SEED_LANDLORD_PASSWORD", _DEFAULT_LANDLORD_PASS)
    stmt = select(User).where(User.phone == phone)
    existing = (await session.execute(stmt)).scalar_one_or_none()
    if existing is not None:
        if existing.role != UserRole.LANDLORD:
            raise SystemExit(f"SEED_LANDLORD_PHONE {phone} is not a landlord user; aborting.")
        return existing
    try:
        return await register_landlord(
            session,
            name="Seed Landlord",
            phone=phone,
            email="landlord.seed@example.test",
            password=password,
        )
    except DuplicateUser as exc:
        raise SystemExit("Unexpected duplicate landlord during seed") from exc


async def _ensure_tenant(session: AsyncSession) -> tuple[User, Tenant]:
    phone = _env("SEED_TENANT_PHONE", _DEFAULT_TENANT_PHONE)
    password = _env("SEED_TENANT_PASSWORD", _DEFAULT_TENANT_PASS)
    stmt = select(User).where(User.phone == phone)
    user = (await session.execute(stmt)).scalar_one_or_none()
    if user is None:
        user = User(
            name="Seed Tenant",
            phone=phone,
            email="tenant.seed@example.test",
            role=UserRole.TENANT,
            password_hash=security.hash_password(password),
            is_verified=True,
            tenant_code="DEV001",
        )
        session.add(user)
        await session.flush()
        tenant = Tenant(user_id=user.id, kyc_status=KycStatus.APPROVED)
        session.add(tenant)
        await session.flush()
    else:
        if user.role != UserRole.TENANT:
            raise SystemExit(f"SEED_TENANT_PHONE {phone} is not a tenant user; aborting.")
        stmt_t = select(Tenant).where(Tenant.user_id == user.id)
        existing_tenant = (await session.execute(stmt_t)).scalar_one_or_none()
        if existing_tenant is None:
            tenant = Tenant(user_id=user.id, kyc_status=KycStatus.APPROVED)
            session.add(tenant)
            await session.flush()
        else:
            tenant = existing_tenant
            if tenant.kyc_status != KycStatus.APPROVED:
                tenant.kyc_status = KycStatus.APPROVED
                await session.flush()
    return user, tenant


async def _ensure_property_and_unit(session: AsyncSession, landlord: User) -> tuple[Property, Unit]:
    stmt = (
        select(Property)
        .where(Property.landlord_id == landlord.id)
        .where(Property.name == _PROPERTY_NAME)
    )
    prop = (await session.execute(stmt)).scalar_one_or_none()
    if prop is None:
        prop = await create_property(
            session,
            landlord=landlord,
            body=PropertyCreate(
                name=_PROPERTY_NAME,
                address="123 Seed Street, Nairobi",
                lat=-1.286389,
                lng=36.817223,
            ),
        )

    stmt_u = (
        select(Unit)
        .where(Unit.property_id == prop.id)
        .where(Unit.label == _UNIT_LABEL)
    )
    unit = (await session.execute(stmt_u)).scalar_one_or_none()
    if unit is None:
        unit = await create_unit(
            session,
            landlord=landlord,
            property_id=prop.id,
            body=UnitCreate(
                label=_UNIT_LABEL,
                bedrooms=2,
                rent_amount=Decimal("25000.00"),
                deposit_amount=Decimal("25000.00"),
                due_day_of_month=5,
            ),
        )
    return prop, unit


async def _ensure_lease(
    session: AsyncSession,
    *,
    landlord: User,
    unit: Unit,
    tenant_row: Tenant,
) -> Lease | None:
    q = select(Lease).where(
        Lease.unit_id == unit.id,
        Lease.tenant_id == tenant_row.id,
        Lease.status == LeaseStatus.ACTIVE,
    )
    existing = (await session.execute(q)).scalar_one_or_none()
    if existing is not None:
        return None
    body = LeaseCreate(
        unit_id=unit.id,
        tenant_id=tenant_row.id,
        start_date=date.today().replace(day=1),
        end_date=None,
        rent_amount=unit.rent_amount,
        deposit_amount=unit.deposit_amount,
        late_fee_rule=LateFeeRule(
            type="flat",
            value=Decimal("500"),
            cadence="once",
            grace_days=3,
            cap_months=6,
        ),
    )
    try:
        return await create_lease(session, landlord=landlord, body=body)
    except LeaseConflict:
        # Another active lease on this unit (e.g. partial seed); treat as done.
        return None


async def run_seed(*, force: bool) -> None:
    settings = get_settings()
    if settings.app_env == "production" and not force:
        print(
            "Refusing to seed: APP_ENV=production. "
            "This loads demonstration accounts into the live database. "
            "If you really intend this, re-run with --force.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    factory = get_session_factory()
    async with factory() as session:
        async with session.begin():
            landlord = await _ensure_landlord(session)
            _tenant_user, tenant_row = await _ensure_tenant(session)
            _prop, unit = await _ensure_property_and_unit(session, landlord)
            lease = await _ensure_lease(session, landlord=landlord, unit=unit, tenant_row=tenant_row)

        # begin() already committed; print after successful commit.
    print("Seed complete.")
    print(f"  Landlord login: {_env('SEED_LANDLORD_PHONE', _DEFAULT_LANDLORD_PHONE)}")
    print(f"  Tenant login:   {_env('SEED_TENANT_PHONE', _DEFAULT_TENANT_PHONE)}")
    print(f"  Property: {_PROPERTY_NAME}, unit {_UNIT_LABEL}")
    if lease is not None:
        print(f"  Created active lease {lease.id}")
    else:
        print("  Active lease already present (skipped create).")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed dev/demo data (idempotent).")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow running when APP_ENV=production (dangerous).",
    )
    args = parser.parse_args()
    asyncio.run(run_seed(force=args.force))


if __name__ == "__main__":
    main()
