"""HTTP routes for leases."""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord
from app.leases import service
from app.leases.models import LeaseStatus
from app.leases.schemas import LeaseCreate, LeaseEnd, LeaseOut
from app.users.models import User

router = APIRouter(prefix="/leases", tags=["leases"])


@router.get("", response_model=list[LeaseOut])
async def list_leases(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
    status_: Optional[LeaseStatus] = Query(default=None, alias="status"),
    unit_id: Optional[uuid.UUID] = None,
    tenant_id: Optional[uuid.UUID] = None,
) -> list[LeaseOut]:
    items = await service.list_leases(
        db, landlord=landlord, status_=status_, unit_id=unit_id, tenant_id=tenant_id
    )
    return [LeaseOut.model_validate(i) for i in items]


@router.post("", response_model=LeaseOut, status_code=status.HTTP_201_CREATED)
async def create_lease(
    body: LeaseCreate,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> LeaseOut:
    try:
        lease = await service.create_lease(db, landlord=landlord, body=body)
    except service.LeaseNotFound:
        raise HTTPException(status_code=404, detail="unit not found")
    except service.TenantNotEligible:
        raise HTTPException(status_code=400, detail="tenant not found")
    except service.LeaseConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return LeaseOut.model_validate(lease)


@router.get("/{lease_id}", response_model=LeaseOut)
async def get_lease(
    lease_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> LeaseOut:
    try:
        lease = await service.get_lease_owned(db, landlord=landlord, lease_id=lease_id)
    except service.LeaseNotFound:
        raise HTTPException(status_code=404, detail="lease not found")
    return LeaseOut.model_validate(lease)


@router.patch("/{lease_id}/end", response_model=LeaseOut)
async def end_lease(
    lease_id: uuid.UUID,
    body: LeaseEnd,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> LeaseOut:
    try:
        lease = await service.end_lease(
            db, landlord=landlord, lease_id=lease_id, body=body
        )
    except service.LeaseNotFound:
        raise HTTPException(status_code=404, detail="lease not found")
    except service.LeaseError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return LeaseOut.model_validate(lease)
