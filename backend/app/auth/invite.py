"""Single-use tenant-invite signed tokens via itsdangerous."""
from __future__ import annotations

from typing import cast

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings

_SALT = "tenant-invite-v1"


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(get_settings().jwt_secret, salt=_SALT)


def issue_invite(user_id: str) -> str:
    """Return a URL-safe token that resolves back to `user_id` for `invite_token_ttl_days`."""
    return _serializer().dumps(user_id)


def parse_invite(token: str) -> str | None:
    """Return the user_id encoded in the token, or `None` if invalid/expired."""
    settings = get_settings()
    max_age = settings.invite_token_ttl_days * 86400
    try:
        return cast(str, _serializer().loads(token, max_age=max_age))
    except (SignatureExpired, BadSignature):
        return None
