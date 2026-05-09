"""arq worker: background jobs (reminders, late-fee accrual, M-Pesa reconciliation)."""
from __future__ import annotations

from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.jobs.daily import daily


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


class WorkerSettings:
    """arq picks this up: `arq app.jobs.worker.WorkerSettings`.

    ``redis_settings`` must be a concrete :class:`RedisSettings` instance: arq's
    ``get_kwargs()`` copies fields from ``WorkerSettings.__dict__`` and does not
    invoke descriptors, so lazy resolution would pass the wrong object into
    ``create_pool`` and crash the worker.
    """

    functions: list = [reconcile_stk, daily]
    cron_jobs: list = [
        # Daily 06:00 EAT == 03:00 UTC
        cron(daily, hour={3}, minute={0}, run_at_startup=False),
        # Hourly STK reconciliation
        cron(reconcile_stk, minute={5}, run_at_startup=False),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
