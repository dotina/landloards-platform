"""SMS OTP — 6-digit codes stored in Redis with TTL."""
from __future__ import annotations

import secrets
from typing import cast

from redis.asyncio import Redis

from app.core.config import get_settings


def _key(user_id: str) -> str:
    return f"otp:{user_id}"


def generate_code() -> str:
    """Cryptographically random 6-digit numeric code."""
    return f"{secrets.randbelow(1_000_000):06d}"


async def issue(redis: Redis, user_id: str) -> str:
    """Generate a code, persist it under `otp:<user_id>` for `otp_ttl_minutes`, and return it."""
    code = generate_code()
    ttl = get_settings().otp_ttl_minutes * 60
    await redis.setex(_key(user_id), ttl, code)
    return code


async def verify(redis: Redis, user_id: str, supplied: str) -> bool:
    """Constant-time-ish verify; consume on success."""
    raw = await redis.get(_key(user_id))
    if raw is None:
        return False
    stored = raw.decode() if isinstance(raw, (bytes, bytearray)) else str(raw)
    if secrets.compare_digest(stored, supplied):
        await redis.delete(_key(user_id))
        return True
    return False


async def open_redis() -> Redis:
    """Convenience constructor used by routes."""
    return cast(Redis, Redis.from_url(get_settings().redis_url))
