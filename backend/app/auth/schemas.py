"""Pydantic schemas for auth requests + responses."""
from __future__ import annotations

import uuid
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class LandlordRegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, description="email or phone")
    password: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserOut(BaseModel):
    id: uuid.UUID
    name: str
    phone: str
    email: Optional[EmailStr] = None
    role: str
    is_verified: bool

    model_config = {"from_attributes": True}


class TenantInviteRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    phone: str = Field(min_length=7, max_length=20)
    email: Optional[EmailStr] = None


class TenantInviteResponse(BaseModel):
    user_id: uuid.UUID
    accept_url: str


class TenantAcceptResolveResponse(BaseModel):
    user_id: uuid.UUID
    name: str
    phone: str


class OtpRequestRequest(BaseModel):
    user_id: uuid.UUID


class OtpVerifyRequest(BaseModel):
    user_id: uuid.UUID
    code: str = Field(min_length=6, max_length=6)


class TenantSetPasswordRequest(BaseModel):
    user_id: uuid.UUID
    code: str = Field(min_length=6, max_length=6, description="OTP code (re-checked)")
    password: str = Field(min_length=8, max_length=128)

    @field_validator("code")
    @classmethod
    def code_is_digits(cls, v: str) -> str:
        if not v.isdigit():
            raise ValueError("code must be 6 digits")
        return v


class ForgotPasswordRequest(BaseModel):
    identifier: str = Field(min_length=1, description="email or phone")


class CsrfTokenResponse(BaseModel):
    csrf_token: str
