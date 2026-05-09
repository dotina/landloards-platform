"""Pydantic schemas for Properties + Units."""
from __future__ import annotations

import uuid
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PropertyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    address: str = Field(min_length=1, max_length=500)
    lat: float | None = None
    lng: float | None = None


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    address: str | None = Field(default=None, min_length=1, max_length=500)
    lat: float | None = None
    lng: float | None = None


class PropertyOut(BaseModel):
    id: uuid.UUID
    landlord_id: uuid.UUID
    name: str
    address: str
    lat: float | None
    lng: float | None
    photo_url: str | None
    model_config = ConfigDict(from_attributes=True)


class UnitCreate(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    bedrooms: int = Field(ge=0, le=50, default=0)
    rent_amount: Decimal = Field(ge=0)
    deposit_amount: Decimal = Field(ge=0)
    due_day_of_month: int = Field(ge=1, le=28, default=1)


class UnitUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=64)
    bedrooms: int | None = Field(default=None, ge=0, le=50)
    rent_amount: Decimal | None = Field(default=None, ge=0)
    deposit_amount: Decimal | None = Field(default=None, ge=0)
    due_day_of_month: int | None = Field(default=None, ge=1, le=28)


class UnitOut(BaseModel):
    id: uuid.UUID
    property_id: uuid.UUID
    label: str
    bedrooms: int
    rent_amount: Decimal
    deposit_amount: Decimal
    due_day_of_month: int
    status: str
    model_config = ConfigDict(from_attributes=True)


class PhotoUploadOut(BaseModel):
    photo_url: str
