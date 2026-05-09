"""Tiny in-memory fakes used by tests in lieu of real Redis / Postgres."""
from __future__ import annotations

import asyncio
import time
from typing import Any


class FakeRedis:
    """Drop-in for the small subset of redis.asyncio.Redis we use.

    Supports: ``get``, ``setex``, ``delete``, ``incr``, ``expire``, ``aclose``.
    Stored values are bytes to match the real client.
    """

    def __init__(self) -> None:
        self._store: dict[str, tuple[bytes, float | None]] = {}
        self._lock = asyncio.Lock()

    def _expired(self, key: str) -> bool:
        if key not in self._store:
            return True
        _, exp = self._store[key]
        if exp is not None and exp <= time.time():
            del self._store[key]
            return True
        return False

    async def setex(self, name: str, time_seconds: int, value: Any) -> bool:
        async with self._lock:
            v = value if isinstance(value, (bytes, bytearray)) else str(value).encode()
            self._store[name] = (bytes(v), time.time() + time_seconds)
        return True

    async def set(self, name: str, value: Any) -> bool:
        async with self._lock:
            v = value if isinstance(value, (bytes, bytearray)) else str(value).encode()
            self._store[name] = (bytes(v), None)
        return True

    async def get(self, name: str) -> bytes | None:
        async with self._lock:
            if self._expired(name):
                return None
            return self._store[name][0]

    async def delete(self, *names: str) -> int:
        n = 0
        async with self._lock:
            for k in names:
                if k in self._store:
                    del self._store[k]
                    n += 1
        return n

    async def incr(self, name: str) -> int:
        async with self._lock:
            if self._expired(name):
                self._store[name] = (b"1", None)
                return 1
            current = int(self._store[name][0])
            new = current + 1
            self._store[name] = (str(new).encode(), self._store[name][1])
            return new

    async def expire(self, name: str, time_seconds: int) -> bool:
        async with self._lock:
            if name not in self._store:
                return False
            v, _ = self._store[name]
            self._store[name] = (v, time.time() + time_seconds)
        return True

    async def ping(self) -> bool:
        return True

    async def aclose(self) -> None:
        return None
