"""arq worker: background jobs (reminders, late-fee accrual, M-Pesa reconciliation).

Later phases register real tasks. For now this module just makes the worker bootable.
"""
from __future__ import annotations

from typing import Any

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger


async def startup(ctx: dict[str, Any]) -> None:
    """Run once on worker boot."""
    configure_logging(level=get_settings().log_level)
    log = get_logger("worker.startup")
    log.info("worker_started")
    ctx["log"] = log


async def reconcile_stk(ctx: dict[str, Any]) -> int:
    """Hourly: find STK payments stuck in PENDING and call stk_query."""
    from app.core.db import get_session_factory
    from app.payments.service import reconcile_pending_stk

    async with get_session_factory()() as session:
        n = await reconcile_pending_stk(session, older_than_seconds=90)
        await session.commit()
    ctx["log"].info("stk_reconcile_pass", failed=n)
    return n


async def shutdown(ctx: dict[str, Any]) -> None:
    """Run once on worker shutdown."""
    ctx["log"].info("worker_stopped")


class _LazyRedisSettings:
    """Class-attribute descriptor that resolves RedisSettings on every access.

    Needed because ``WorkerSettings`` is read at module-import time but
    REDIS_URL may be set later (e.g. by tests). arq accesses this attribute
    once at worker start, so per-access cost is irrelevant in production.
    """

    def __get__(self, _obj: object, _objtype: type | None = None) -> RedisSettings:
        return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    """arq picks this up: `arq app.jobs.worker.WorkerSettings`."""

    functions: list = [reconcile_stk]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _LazyRedisSettings()
