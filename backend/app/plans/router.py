"""HTTP routes for payment plans."""
from __future__ import annotations

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord, require_tenant
from app.plans import service
from app.plans.models import PaymentPlanStatus
from app.plans.schemas import PlanDecision, PlanOut, PlanRequest
from app.tenants.service import get_tenant_by_user_id
from app.users.models import User

tenant_router = APIRouter(prefix="/plans", tags=["plans"])


@tenant_router.post("", response_model=PlanOut, status_code=201)
async def request_plan(
    body: PlanRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> PlanOut:
    tenant = await get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant profile not found")
    try:
        plan = await service.request_plan(db, tenant_id=tenant.id, body=body)
    except service.PlanIneligible as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await db.commit()
    return PlanOut.model_validate(plan)


@tenant_router.get("/me", response_model=list[PlanOut])
async def list_my_plans(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> list[PlanOut]:
    tenant = await get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        return []
    rows = await service.list_for_tenant(db, tenant_id=tenant.id)
    return [PlanOut.model_validate(r) for r in rows]


admin_router = APIRouter(prefix="/admin/plans", tags=["admin-plans"])


@admin_router.get("", response_model=list[PlanOut])
async def list_plans(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
    status_: Optional[PaymentPlanStatus] = Query(default=None, alias="status"),
) -> list[PlanOut]:
    rows = await service.list_for_landlord(db, landlord=landlord, status_=status_)
    return [PlanOut.model_validate(r) for r in rows]


@admin_router.post("/{plan_id}/decision", response_model=PlanOut)
async def decide_plan(
    plan_id: uuid.UUID,
    body: PlanDecision,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> PlanOut:
    try:
        plan = await service.decide_plan(
            db, landlord=landlord, plan_id=plan_id, body=body
        )
    except service.PlanNotFound:
        raise HTTPException(status_code=404, detail="plan not found")
    except service.PlanError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()
    return PlanOut.model_validate(plan)
