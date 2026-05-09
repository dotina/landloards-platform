"""HTTP routes for tenants + KYC."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord, require_tenant
from app.core.storage import presigned_get_url, put_object
from app.tenants import service
from app.tenants.schemas import (
    KycDecisionRequest,
    KycPresignedUrlOut,
    KycUploadOut,
    TenantProfile,
    TenantUpdateProfile,
)
from app.users.models import User

ALLOWED_KYC_TYPES = {"image/jpeg", "image/png", "application/pdf"}
MAX_KYC_BYTES = 10 * 1024 * 1024
KYC_PRESIGNED_TTL = 5 * 60  # 5 min per design §3.3

# ─── Tenant-side ────────────────────────────────────────────────────
tenant_router = APIRouter(prefix="/tenant", tags=["tenant"])


@tenant_router.get("/me", response_model=TenantProfile)
async def my_profile(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> TenantProfile:
    tenant = await service.get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant profile not found")
    return TenantProfile(
        id=tenant.id,
        user_id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        tenant_code=user.tenant_code,
        kyc_status=tenant.kyc_status.value,
        kyc_rejected_reason=tenant.kyc_rejected_reason,
        employer=tenant.employer,
        next_of_kin=tenant.next_of_kin,
        has_id_doc=tenant.id_doc_url is not None,
    )


@tenant_router.patch("/me", response_model=TenantProfile)
async def update_my_profile(
    body: TenantUpdateProfile,
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> TenantProfile:
    tenant = await service.get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant profile not found")
    tenant = await service.update_tenant_profile(db, tenant=tenant, body=body)
    await db.commit()
    return TenantProfile(
        id=tenant.id,
        user_id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        tenant_code=user.tenant_code,
        kyc_status=tenant.kyc_status.value,
        kyc_rejected_reason=tenant.kyc_rejected_reason,
        employer=tenant.employer,
        next_of_kin=tenant.next_of_kin,
        has_id_doc=tenant.id_doc_url is not None,
    )


@tenant_router.post("/kyc/upload", response_model=KycUploadOut)
async def upload_kyc(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
    file: UploadFile = File(...),
) -> KycUploadOut:
    if file.content_type not in ALLOWED_KYC_TYPES:
        raise HTTPException(status_code=415, detail="unsupported file type")
    blob = await file.read()
    if len(blob) > MAX_KYC_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds 10 MiB")
    tenant = await service.get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant profile not found")

    ext = (file.filename or "doc").rsplit(".", 1)[-1].lower() or "bin"
    key = f"kyc/{tenant.id}/{uuid.uuid4()}.{ext}"
    put_object(key=key, data=blob, content_type=file.content_type)

    tenant = await service.attach_kyc_doc(db, tenant=tenant, key=key)
    await db.commit()
    return KycUploadOut(kyc_status=tenant.kyc_status.value)


# ─── Admin-side (landlord) ──────────────────────────────────────────
admin_router = APIRouter(prefix="/admin/tenants", tags=["admin-tenants"])


@admin_router.get("", response_model=list[TenantProfile])
async def list_tenants(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],  # noqa: ARG001
) -> list[TenantProfile]:
    rows = await service.list_tenants(db)
    return [
        TenantProfile(
            id=t.id,
            user_id=u.id,
            name=u.name,
            phone=u.phone,
            email=u.email,
            tenant_code=u.tenant_code,
            kyc_status=t.kyc_status.value,
            kyc_rejected_reason=t.kyc_rejected_reason,
            employer=t.employer,
            next_of_kin=t.next_of_kin,
            has_id_doc=t.id_doc_url is not None,
        )
        for t, u in rows
    ]


@admin_router.get("/{tenant_id}", response_model=TenantProfile)
async def get_tenant(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],  # noqa: ARG001
) -> TenantProfile:
    try:
        t, u = await service.get_tenant(db, tenant_id=tenant_id)
    except service.TenantNotFound:
        raise HTTPException(status_code=404, detail="tenant not found")
    return TenantProfile(
        id=t.id,
        user_id=u.id,
        name=u.name,
        phone=u.phone,
        email=u.email,
        tenant_code=u.tenant_code,
        kyc_status=t.kyc_status.value,
        kyc_rejected_reason=t.kyc_rejected_reason,
        employer=t.employer,
        next_of_kin=t.next_of_kin,
        has_id_doc=t.id_doc_url is not None,
    )


@admin_router.get("/{tenant_id}/kyc/url", response_model=KycPresignedUrlOut)
async def kyc_presigned_url(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],  # noqa: ARG001
) -> KycPresignedUrlOut:
    try:
        t, _ = await service.get_tenant(db, tenant_id=tenant_id)
    except service.TenantNotFound:
        raise HTTPException(status_code=404, detail="tenant not found")
    if t.id_doc_url is None:
        raise HTTPException(status_code=404, detail="no KYC doc uploaded")
    url = presigned_get_url(key=t.id_doc_url, expires_seconds=KYC_PRESIGNED_TTL)
    return KycPresignedUrlOut(url=url, expires_in_seconds=KYC_PRESIGNED_TTL)


@admin_router.post("/{tenant_id}/kyc/decision", response_model=TenantProfile)
async def kyc_decide(
    tenant_id: uuid.UUID,
    body: KycDecisionRequest,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> TenantProfile:
    try:
        tenant = await service.decide_kyc(
            db, actor=landlord, tenant_id=tenant_id, body=body
        )
    except service.TenantNotFound:
        raise HTTPException(status_code=404, detail="tenant not found")
    except service.KycInvalidState as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    await db.commit()

    _, user = await service.get_tenant(db, tenant_id=tenant.id)
    return TenantProfile(
        id=tenant.id,
        user_id=user.id,
        name=user.name,
        phone=user.phone,
        email=user.email,
        tenant_code=user.tenant_code,
        kyc_status=tenant.kyc_status.value,
        kyc_rejected_reason=tenant.kyc_rejected_reason,
        employer=tenant.employer,
        next_of_kin=tenant.next_of_kin,
        has_id_doc=tenant.id_doc_url is not None,
    )
