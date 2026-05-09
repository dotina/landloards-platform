"""FastAPI dependencies for the auth layer."""
from __future__ import annotations

import uuid
from collections.abc import Awaitable, Callable
from typing import Annotated

import jwt
from fastapi import Cookie, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth import security
from app.users.models import User, UserRole

ACCESS_COOKIE = "ll_access"
REFRESH_COOKIE = "ll_refresh"
CSRF_COOKIE = "ll_csrf"
CSRF_HEADER = "x-csrf-token"


async def get_current_user(
    db: Annotated[AsyncSession, Depends(db_session)],
    access_token: Annotated[str | None, Cookie(alias=ACCESS_COOKIE)] = None,
) -> User:
    if access_token is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not authenticated")
    try:
        payload = security.decode_token(access_token, expected_type="access")
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid token") from exc
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="malformed token") from exc

    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user gone")
    return user


def require_role(*roles: UserRole) -> Callable[..., Awaitable[User]]:
    """Dependency factory: 403 unless the current user has one of `roles`."""

    async def _dep(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
        return user

    return _dep


require_landlord = require_role(UserRole.LANDLORD, UserRole.ADMIN)
require_tenant = require_role(UserRole.TENANT)
require_admin = require_role(UserRole.ADMIN)


async def csrf_double_submit(
    csrf_cookie: Annotated[str | None, Cookie(alias=CSRF_COOKIE)] = None,
    csrf_header: Annotated[str | None, Header(alias=CSRF_HEADER)] = None,
) -> None:
    """Reject state-changing requests where cookie and header don't match.

    Login mints a CSRF token, sets a non-httpOnly cookie *and* returns the
    token in the response body so the frontend can echo it via the
    ``X-CSRF-Token`` header on subsequent state-changing calls.
    """
    if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="csrf failure")
