"""Resend email sender."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import get_settings


class EmailSendError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class EmailResult:
    provider_message_id: Optional[str]
    raw: dict


async def send_email(
    *,
    to: str,
    subject: str,
    text: str,
    html: Optional[str] = None,
    client: Optional[httpx.AsyncClient] = None,
) -> EmailResult:
    settings = get_settings()
    headers = {
        "Authorization": f"Bearer {settings.resend_api_key}",
        "Content-Type": "application/json",
    }
    payload: dict = {
        "from": settings.email_from,
        "to": [to],
        "subject": subject,
        "text": text,
    }
    if html is not None:
        payload["html"] = html

    async def _do(c: httpx.AsyncClient) -> httpx.Response:
        return await c.post(
            f"{settings.resend_base_url}/emails", json=payload, headers=headers
        )

    if client is None:
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await _do(c)
    else:
        resp = await _do(client)

    if resp.status_code >= 400:
        raise EmailSendError(f"Resend HTTP {resp.status_code}: {resp.text[:200]}")
    body = resp.json()
    return EmailResult(provider_message_id=body.get("id"), raw=body)
