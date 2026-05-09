"""Pydantic schemas for tenants + KYC."""
from __future__ import annotations

import uuid
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class NextOfKin(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    relationship: str = Field(min_length=1, max_length=64)
    phone: str = Field(min_length=7, max_length=20)


class TenantProfile(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    phone: str
    email: str | None = None
    tenant_code: str | None = None
    kyc_status: str
    kyc_rejected_reason: str | None = None
    employer: str | None = None
    next_of_kin: dict[str, Any] | None = None
    has_id_doc: bool

    model_config = ConfigDict(from_attributes=True)


class TenantUpdateProfile(BaseModel):
    employer: str | None = Field(default=None, max_length=255)
    next_of_kin: NextOfKin | None = None


class KycDecisionRequest(BaseModel):
    action: Literal["approve", "reject"]
    reason: str | None = Field(default=None, max_length=500)


class KycPresignedUrlOut(BaseModel):
    url: str
    expires_in_seconds: int


class KycUploadOut(BaseModel):
    kyc_status: str
