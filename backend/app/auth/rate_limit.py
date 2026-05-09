"""Simple Redis-backed fixed-window rate limiter."""
from __future__ import annotations

from typing import Protocol


class _RedisLike(Protocol):
    async def incr(self, name: str) -> int: ...
    async def expire(self, name: str, time: int) -> bool: ...


async def hit(
    redis: _RedisLike,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """Increment the bucket and return True if the request is within the limit.

    The first hit in a window seeds TTL; subsequent hits in the same window
    reuse it. After ``window_seconds`` the counter resets.
    """
    count = await redis.incr(bucket)
    if count == 1:
        await redis.expire(bucket, window_seconds)
    return count <= limit
