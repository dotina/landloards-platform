"""Daraja HTTP client — OAuth + STK Push + STK Query."""
from __future__ import annotations

import base64
import datetime as _dt
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import get_settings


class DarajaError(Exception):
    pass


@dataclass(frozen=True, slots=True)
class StkPushResult:
    checkout_request_id: str
    merchant_request_id: str
    response_description: str


@dataclass(frozen=True, slots=True)
class StkQueryResult:
    result_code: str
    result_desc: str


def _base_url() -> str:
    settings = get_settings()
    return (
        "https://sandbox.safaricom.co.ke"
        if settings.mpesa_env == "sandbox"
        else "https://api.safaricom.co.ke"
    )


def _basic_auth_header() -> str:
    settings = get_settings()
    raw = f"{settings.mpesa_consumer_key}:{settings.mpesa_consumer_secret}".encode()
    return f"Basic {base64.b64encode(raw).decode('ascii')}"


def _stk_password(*, timestamp: str) -> str:
    settings = get_settings()
    raw = f"{settings.mpesa_business_short_code}{settings.mpesa_passkey}{timestamp}"
    return base64.b64encode(raw.encode("utf-8")).decode("ascii")


def _now_timestamp() -> str:
    return _dt.datetime.now().strftime("%Y%m%d%H%M%S")


async def get_access_token(client: Optional[httpx.AsyncClient] = None) -> str:
    """Daraja OAuth: returns a short-lived bearer token."""
    url = f"{_base_url()}/oauth/v1/generate?grant_type=client_credentials"

    async def _do(c: httpx.AsyncClient) -> httpx.Response:
        return await c.get(url, headers={"Authorization": _basic_auth_header()})

    if client is None:
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await _do(c)
    else:
        resp = await _do(client)

    if resp.status_code >= 400:
        raise DarajaError(f"OAuth HTTP {resp.status_code}: {resp.text[:200]}")
    return resp.json().get("access_token") or ""


async def stk_push(
    *,
    phone: str,
    amount: int,
    account_reference: str,
    transaction_desc: str,
    callback_url: str,
    client: Optional[httpx.AsyncClient] = None,
) -> StkPushResult:
    """Initiate an STK push.

    `phone` must be in 254-prefixed format (no leading +).
    `amount` must be a whole number of KES (Daraja rejects fractional).
    """
    settings = get_settings()
    timestamp = _now_timestamp()
    payload = {
        "BusinessShortCode": settings.mpesa_business_short_code,
        "Password": _stk_password(timestamp=timestamp),
        "Timestamp": timestamp,
        "TransactionType": "CustomerPayBillOnline",
        "Amount": int(amount),
        "PartyA": phone,
        "PartyB": settings.mpesa_business_short_code,
        "PhoneNumber": phone,
        "CallBackURL": callback_url,
        "AccountReference": account_reference[:12],
        "TransactionDesc": transaction_desc[:13],
    }

    token = await get_access_token(client=client)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{_base_url()}/mpesa/stkpush/v1/processrequest"

    async def _do(c: httpx.AsyncClient) -> httpx.Response:
        return await c.post(url, headers=headers, json=payload)

    if client is None:
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await _do(c)
    else:
        resp = await _do(client)

    body = resp.json() if resp.content else {}
    if resp.status_code >= 400 or body.get("ResponseCode", "1") != "0":
        raise DarajaError(
            f"STK push failed HTTP {resp.status_code}: {body or resp.text[:200]}"
        )
    return StkPushResult(
        checkout_request_id=body["CheckoutRequestID"],
        merchant_request_id=body["MerchantRequestID"],
        response_description=body.get("ResponseDescription", ""),
    )


async def stk_query(
    *, checkout_request_id: str, client: Optional[httpx.AsyncClient] = None
) -> StkQueryResult:
    settings = get_settings()
    timestamp = _now_timestamp()
    token = await get_access_token(client=client)
    payload = {
        "BusinessShortCode": settings.mpesa_business_short_code,
        "Password": _stk_password(timestamp=timestamp),
        "Timestamp": timestamp,
        "CheckoutRequestID": checkout_request_id,
    }
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    url = f"{_base_url()}/mpesa/stkpushquery/v1/query"

    async def _do(c: httpx.AsyncClient) -> httpx.Response:
        return await c.post(url, headers=headers, json=payload)

    if client is None:
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await _do(c)
    else:
        resp = await _do(client)

    if resp.status_code >= 400:
        raise DarajaError(f"STK query HTTP {resp.status_code}: {resp.text[:200]}")
    body = resp.json() if resp.content else {}
    return StkQueryResult(
        result_code=str(body.get("ResultCode", "")),
        result_desc=str(body.get("ResultDesc", "")),
    )
