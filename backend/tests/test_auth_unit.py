"""Pure-unit tests for auth helpers — no DB, no Redis."""
from __future__ import annotations

import time

import jwt
import pytest

from app.auth import invite as invite_mod
from app.auth import otp as otp_mod
from app.auth import rate_limit, security
from app.auth.service import _generate_tenant_code, generate_csrf_token, is_strong_password
from tests.fakes import FakeRedis


def test_argon2_round_trip() -> None:
    h = security.hash_password("correct horse battery staple")
    assert security.verify_password("correct horse battery staple", h)
    assert not security.verify_password("wrong", h)


def test_jwt_round_trip_access_and_refresh() -> None:
    a = security.create_token(subject="u-1", type_="access")
    r = security.create_token(subject="u-1", type_="refresh")
    assert security.decode_token(a, expected_type="access")["sub"] == "u-1"
    assert security.decode_token(r, expected_type="refresh")["sub"] == "u-1"

    with pytest.raises(jwt.InvalidTokenError):
        security.decode_token(a, expected_type="refresh")


def test_jwt_expired_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    """A token whose iat/exp lies in the past must fail verification."""
    monkeypatch.setenv("JWT_ACCESS_TTL_MINUTES", "0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    tok = security.create_token(subject="u-1", type_="access")
    time.sleep(1.1)  # tokens minted with exp = now ⇒ now+1s definitely expired
    with pytest.raises(jwt.ExpiredSignatureError):
        security.decode_token(tok, expected_type="access")


def test_invite_round_trip() -> None:
    tok = invite_mod.issue_invite("u-2")
    assert invite_mod.parse_invite(tok) == "u-2"


def test_invite_tampered_returns_none() -> None:
    tok = invite_mod.issue_invite("u-3")
    assert invite_mod.parse_invite(tok + "x") is None


def test_invite_expired_returns_none(monkeypatch: pytest.MonkeyPatch) -> None:
    """A token older than `invite_token_ttl_days` must be rejected."""
    monkeypatch.setenv("INVITE_TOKEN_TTL_DAYS", "0")
    from app.core.config import get_settings

    get_settings.cache_clear()

    tok = invite_mod.issue_invite("u-4")
    time.sleep(1.1)
    assert invite_mod.parse_invite(tok) is None


@pytest.mark.asyncio
async def test_otp_round_trip() -> None:
    redis = FakeRedis()
    code = await otp_mod.issue(redis, "u-5")
    assert len(code) == 6 and code.isdigit()
    assert await otp_mod.verify(redis, "u-5", code)
    # Single-use: second verify must fail
    assert not await otp_mod.verify(redis, "u-5", code)


@pytest.mark.asyncio
async def test_otp_wrong_code_rejected() -> None:
    redis = FakeRedis()
    await otp_mod.issue(redis, "u-6")
    assert not await otp_mod.verify(redis, "u-6", "000000")


@pytest.mark.asyncio
async def test_rate_limit_allows_within_window_and_blocks_after() -> None:
    redis = FakeRedis()
    for _ in range(3):
        assert await rate_limit.hit(redis, bucket="rl:test", limit=3, window_seconds=60)
    assert not await rate_limit.hit(redis, bucket="rl:test", limit=3, window_seconds=60)


def test_is_strong_password_policy() -> None:
    assert is_strong_password("abc12345")
    assert not is_strong_password("short1")
    assert not is_strong_password("alllettersxyz")
    assert not is_strong_password("12345678")


def test_tenant_code_format() -> None:
    code = _generate_tenant_code()
    assert len(code) == 6
    assert code.isalnum() and code.upper() == code


def test_csrf_token_uniqueness() -> None:
    a = generate_csrf_token()
    b = generate_csrf_token()
    assert a != b and len(a) >= 30
