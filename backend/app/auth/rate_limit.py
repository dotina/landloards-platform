"""Simple Redis-backed fixed-window rate limiter."""
from __future__ import annotations

from redis.asyncio import Redis


async def hit(
    redis: Redis,
    *,
    bucket: str,
    limit: int,
    window_seconds: int,
) -> bool:
    """Increment the bucket and return True if the request is within the limit.

    The first hit in a window seeds TTL; subsequent hits in the same window
    reuse it. After ``window_seconds`` the counter resets.
    """
    count_raw = await redis.incr(bucket)
    count = int(count_raw)
    if count == 1:
        await redis.expire(bucket, window_seconds)
    return count <= limit
