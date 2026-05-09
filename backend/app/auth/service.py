"""Auth business logic — pure functions over an AsyncSession."""
from __future__ import annotations

import re
import secrets
import string
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import invite as invite_mod
from app.auth import security
from app.tenants.models import KycStatus, Tenant
from app.users.models import User, UserRole

_PASSWORD_RE = re.compile(r"(?=.*[A-Za-z])(?=.*\d).{8,128}")
_TENANT_CODE_ALPHABET = string.ascii_uppercase + string.digits


class AuthError(Exception):
    """Base auth exception."""


class DuplicateUser(AuthError):
    """Phone or email already exists."""


class InvalidCredentials(AuthError):
    """Authentication failed."""


class InvalidInviteToken(AuthError):
    """Invite token is malformed, expired, or already accepted."""


def is_strong_password(value: str) -> bool:
    """Lower bound: 8+ chars with at least one letter and one digit."""
    return bool(_PASSWORD_RE.fullmatch(value))


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def _generate_tenant_code() -> str:
    """6-char uppercase alnum, ambiguous chars (0/O, 1/I) preserved.

    Uniqueness enforced by DB; on collision, caller retries.
    """
    return "".join(secrets.choice(_TENANT_CODE_ALPHABET) for _ in range(6))


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID | str) -> Optional[User]:
    if isinstance(user_id, str):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError:
            return None
    return await db.get(User, user_id)


async def get_user_by_identifier(db: AsyncSession, identifier: str) -> Optional[User]:
    """Look up by phone OR email."""
    stmt = select(User).where(or_(User.phone == identifier, User.email == identifier))
    return (await db.execute(stmt)).scalar_one_or_none()


async def register_landlord(
    db: AsyncSession,
    *,
    name: str,
    phone: str,
    email: str,
    password: str,
) -> User:
    user = User(
        name=name,
        phone=phone,
        email=email,
        role=UserRole.LANDLORD,
        password_hash=security.hash_password(password),
        is_verified=True,  # landlord self-signup is auto-verified for MVP
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateUser() from exc
    return user


async def authenticate(db: AsyncSession, *, identifier: str, password: str) -> User:
    user = await get_user_by_identifier(db, identifier)
    if user is None or not security.verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return user


async def create_tenant_invite(
    db: AsyncSession,
    *,
    landlord: User,
    name: str,
    phone: str,
    email: Optional[str],
) -> tuple[User, str]:
    """Insert an unverified Tenant + User shell and return the signed invite token."""
    if landlord.role not in (UserRole.LANDLORD, UserRole.ADMIN):
        raise AuthError("only landlord may invite")

    code = _generate_tenant_code()
    user = User(
        name=name,
        phone=phone,
        email=email,
        role=UserRole.TENANT,
        password_hash="!",  # unusable until set via OTP flow
        is_verified=False,
        tenant_code=code,
    )
    db.add(user)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise DuplicateUser() from exc

    tenant = Tenant(user_id=user.id, kyc_status=KycStatus.PENDING)
    db.add(tenant)
    await db.flush()

    token = invite_mod.issue_invite(str(user.id))
    return user, token


async def resolve_invite(db: AsyncSession, token: str) -> User:
    user_id = invite_mod.parse_invite(token)
    if user_id is None:
        raise InvalidInviteToken()
    user = await get_user_by_id(db, user_id)
    if user is None or user.role != UserRole.TENANT:
        raise InvalidInviteToken()
    if user.is_verified:
        # Already accepted — token is single-use semantically.
        raise InvalidInviteToken()
    return user


async def set_tenant_password(
    db: AsyncSession, *, user_id: uuid.UUID, new_password: str
) -> User:
    user = await db.get(User, user_id)
    if user is None or user.role != UserRole.TENANT:
        raise InvalidInviteToken()
    user.password_hash = security.hash_password(new_password)
    user.is_verified = True
    user.updated_at = datetime.utcnow()  # explicit so tests don't sleep
    await db.flush()
    return user
