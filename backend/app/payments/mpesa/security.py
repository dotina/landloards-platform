"""HMAC-signed M-Pesa callback URLs.

Daraja calls our public webhook with a signed token in the path. The
signature binds the token to ``checkout_request_id`` so an attacker who
guesses a checkout cannot forge a callback for another payment.

Callback URL shape: ``/webhooks/mpesa/stk/{token}``.
The token is ``base64url(checkout_request_id + '|' + sig)`` where
``sig = HMAC-SHA256(secret, checkout_request_id)``.
"""
from __future__ import annotations

import base64
import hashlib
import hmac


def make_token(checkout_request_id: str, *, secret: str) -> str:
    sig = hmac.new(
        secret.encode("utf-8"), checkout_request_id.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    raw = f"{checkout_request_id}|{sig}".encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def parse_token(token: str, *, secret: str) -> str | None:
    """Return the checkout_request_id encoded in `token` if the signature
    verifies; otherwise return None.
    """
    pad = "=" * (-len(token) % 4)
    try:
        raw = base64.urlsafe_b64decode((token + pad).encode("ascii"))
    except Exception:
        return None
    text = raw.decode("utf-8", errors="ignore")
    if "|" not in text:
        return None
    cid, _, sig = text.partition("|")
    expected = hmac.new(
        secret.encode("utf-8"), cid.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    return cid


def callback_url(checkout_request_id: str, *, base_url: str, secret: str) -> str:
    token = make_token(checkout_request_id, secret=secret)
    return f"{base_url.rstrip('/')}/webhooks/mpesa/stk/{token}"
