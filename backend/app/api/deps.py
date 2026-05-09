"""FastAPI dependencies used by route handlers."""
from __future__ import annotations

from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session


async def db_session() -> AsyncIterator[AsyncSession]:
    """Yield a per-request `AsyncSession`."""
    async for session in get_session():
        yield session
