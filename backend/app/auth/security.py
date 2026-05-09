"""Password hashing (argon2) + JWT encode/decode."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Literal

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.config import get_settings

# Argon2id with library-recommended params (per design §3.3).
_hasher = PasswordHasher()

JwtType = Literal["access", "refresh"]


def hash_password(plaintext: str) -> str:
    """Hash a plaintext password using argon2id."""
    return _hasher.hash(plaintext)


def verify_password(plaintext: str, hashed: str) -> bool:
    """Constant-time verify."""
    try:
        return _hasher.verify(hashed, plaintext)
    except VerifyMismatchError:
        return False


def create_token(*, subject: str, type_: JwtType, extra: dict[str, Any] | None = None) -> str:
    """Create a signed JWT.

    `subject` is conventionally the user UUID as a string.
    """
    settings = get_settings()
    now = datetime.now(tz=timezone.utc)
    if type_ == "access":
        exp = now + timedelta(minutes=settings.jwt_access_ttl_minutes)
    else:
        exp = now + timedelta(days=settings.jwt_refresh_ttl_days)
    payload: dict[str, Any] = {
        "sub": subject,
        "iat": int(now.timestamp()),
        "exp": int(exp.timestamp()),
        "type": type_,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_token(token: str, *, expected_type: JwtType) -> dict[str, Any]:
    """Decode and validate a JWT. Raises `jwt.PyJWTError` on failure."""
    settings = get_settings()
    payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    if payload.get("type") != expected_type:
        raise jwt.InvalidTokenError(f"expected token type {expected_type!r}")
    return payload
