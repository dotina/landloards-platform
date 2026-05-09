"""Africa's Talking SMS sender — minimal HTTP client."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import get_settings


class SmsSendError(Exception):
    """Permanent or transient failure from Africa's Talking."""


@dataclass(frozen=True, slots=True)
class SmsResult:
    provider_message_id: str | None
    cost: str | None
    raw: dict[str, Any]


async def send_sms(
    *,
    phone: str,
    body: str,
    client: httpx.AsyncClient | None = None,
) -> SmsResult:
    """POST to Africa's Talking sandbox or prod, return parsed result."""
    settings = get_settings()
    headers = {
        "apiKey": settings.at_api_key,
        "Content-Type": "application/x-www-form-urlencoded",
        "Accept": "application/json",
    }
    payload = {
        "username": settings.at_username,
        "to": phone,
        "message": body,
        "from": settings.at_sender_id,
    }

    async def _do(c: httpx.AsyncClient) -> httpx.Response:
        return await c.post(f"{settings.at_base_url}/messaging", data=payload, headers=headers)

    if client is None:
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await _do(c)
    else:
        resp = await _do(client)

    if resp.status_code >= 400:
        raise SmsSendError(f"AT HTTP {resp.status_code}: {resp.text[:200]}")
    body_json = resp.json()
    recipients = (body_json.get("SMSMessageData") or {}).get("Recipients") or []
    if not recipients:
        raise SmsSendError(f"AT returned no recipients: {body_json}")
    rec = recipients[0]
    if str(rec.get("status")).lower() not in ("success", "sent"):
        raise SmsSendError(f"AT recipient status {rec.get('status')!r}: {rec}")
    return SmsResult(
        provider_message_id=str(rec.get("messageId")) if rec.get("messageId") else None,
        cost=rec.get("cost"),
        raw=body_json,
    )
