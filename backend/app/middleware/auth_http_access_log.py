"""Structured access logging for `/auth/*` (session / login flows).

Complements uvicorn access logs so deployers can correlate API + SPA behavior
without scraping mixed formats.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable

from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

_log = get_logger("http.auth")


def _client_host(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else ""


async def auth_http_access_logger(
    request: Request,
    call_next: Callable[[Request], Awaitable[Response]],
) -> Response:
    path = request.url.path
    if not path.startswith("/auth"):
        return await call_next(request)

    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        ms = round((time.perf_counter() - started) * 1000, 2)
        _log.warning(
            "auth_request_unhandled",
            method=request.method,
            path=path,
            duration_ms=ms,
            client=_client_host(request),
        )
        raise

    ms = round((time.perf_counter() - started) * 1000, 2)
    _log.info(
        "auth_request",
        method=request.method,
        path=path,
        status=response.status_code,
        duration_ms=ms,
        client=_client_host(request),
    )
    return response
