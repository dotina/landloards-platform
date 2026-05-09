"""HTTP routes for Properties + Units."""
from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord
from app.core.storage import presigned_get_url, put_object
from app.properties import service
from app.properties.schemas import (
    PhotoUploadOut,
    PropertyCreate,
    PropertyOut,
    PropertyUpdate,
    UnitCreate,
    UnitOut,
    UnitUpdate,
)
from app.users.models import User

ALLOWED_PHOTO_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_PHOTO_BYTES = 5 * 1024 * 1024  # 5 MiB

router = APIRouter(prefix="/properties", tags=["properties"])


@router.get("", response_model=list[PropertyOut])
async def list_properties(
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> list[PropertyOut]:
    items = await service.list_properties(db, landlord=landlord)
    return [PropertyOut.model_validate(i) for i in items]


@router.post("", response_model=PropertyOut, status_code=status.HTTP_201_CREATED)
async def create_property(
    body: PropertyCreate,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> PropertyOut:
    p = await service.create_property(db, landlord=landlord, body=body)
    await db.commit()
    return PropertyOut.model_validate(p)


@router.get("/{property_id}", response_model=PropertyOut)
async def get_property(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> PropertyOut:
    try:
        p = await service.get_property_owned(db, landlord=landlord, property_id=property_id)
    except service.PropertyNotFound:
        raise HTTPException(status_code=404, detail="property not found")
    return PropertyOut.model_validate(p)


@router.patch("/{property_id}", response_model=PropertyOut)
async def update_property(
    property_id: uuid.UUID,
    body: PropertyUpdate,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> PropertyOut:
    try:
        p = await service.update_property(
            db, landlord=landlord, property_id=property_id, body=body
        )
    except service.PropertyNotFound:
        raise HTTPException(status_code=404, detail="property not found")
    await db.commit()
    return PropertyOut.model_validate(p)


@router.delete("/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_property(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> None:
    try:
        await service.delete_property(db, landlord=landlord, property_id=property_id)
    except service.PropertyNotFound:
        raise HTTPException(status_code=404, detail="property not found")
    await db.commit()


# ─── Photo upload ────────────────────────────────────────────────────
@router.post("/{property_id}/photo", response_model=PhotoUploadOut)
async def upload_property_photo(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
    file: UploadFile = File(...),
) -> PhotoUploadOut:
    if file.content_type not in ALLOWED_PHOTO_TYPES:
        raise HTTPException(status_code=415, detail="unsupported image type")
    blob = await file.read()
    if len(blob) > MAX_PHOTO_BYTES:
        raise HTTPException(status_code=413, detail="image exceeds 5 MiB")
    try:
        await service.get_property_owned(db, landlord=landlord, property_id=property_id)
    except service.PropertyNotFound:
        raise HTTPException(status_code=404, detail="property not found")

    ext = (file.filename or "img").rsplit(".", 1)[-1].lower() or "bin"
    key = f"properties/{property_id}/{uuid.uuid4()}.{ext}"
    put_object(key=key, data=blob, content_type=file.content_type)

    photo_url = presigned_get_url(key=key, expires_seconds=86400)
    p = await service.set_property_photo(
        db, landlord=landlord, property_id=property_id, photo_url=photo_url
    )
    await db.commit()
    return PhotoUploadOut(photo_url=p.photo_url or photo_url)


# ─── Units ───────────────────────────────────────────────────────────
@router.get("/{property_id}/units", response_model=list[UnitOut])
async def list_units(
    property_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> list[UnitOut]:
    try:
        items = await service.list_units(db, landlord=landlord, property_id=property_id)
    except service.PropertyNotFound:
        raise HTTPException(status_code=404, detail="property not found")
    return [UnitOut.model_validate(i) for i in items]


@router.post(
    "/{property_id}/units", response_model=UnitOut, status_code=status.HTTP_201_CREATED
)
async def create_unit(
    property_id: uuid.UUID,
    body: UnitCreate,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> UnitOut:
    try:
        u = await service.create_unit(
            db, landlord=landlord, property_id=property_id, body=body
        )
    except service.PropertyNotFound:
        raise HTTPException(status_code=404, detail="property not found")
    await db.commit()
    return UnitOut.model_validate(u)


# Top-level unit routes
units_router = APIRouter(prefix="/units", tags=["units"])


@units_router.get("/{unit_id}", response_model=UnitOut)
async def get_unit(
    unit_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> UnitOut:
    try:
        u = await service.get_unit_owned(db, landlord=landlord, unit_id=unit_id)
    except service.UnitNotFound:
        raise HTTPException(status_code=404, detail="unit not found")
    return UnitOut.model_validate(u)


@units_router.patch("/{unit_id}", response_model=UnitOut)
async def update_unit(
    unit_id: uuid.UUID,
    body: UnitUpdate,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> UnitOut:
    try:
        u = await service.update_unit(db, landlord=landlord, unit_id=unit_id, body=body)
    except service.UnitNotFound:
        raise HTTPException(status_code=404, detail="unit not found")
    await db.commit()
    return UnitOut.model_validate(u)


@units_router.delete("/{unit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_unit(
    unit_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> None:
    try:
        await service.delete_unit(db, landlord=landlord, unit_id=unit_id)
    except service.UnitNotFound:
        raise HTTPException(status_code=404, detail="unit not found")
    except service.UnitInUse:
        raise HTTPException(status_code=409, detail="unit has an active lease")
    await db.commit()
