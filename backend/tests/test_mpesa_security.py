"""HMAC-signed callback URL — round-trip + tampering tests."""
from __future__ import annotations

from app.payments.mpesa.security import callback_url, make_token, parse_token


def test_token_round_trip() -> None:
    cid = "ws_CO_1234567890"
    secret = "topsecret"
    token = make_token(cid, secret=secret)
    assert parse_token(token, secret=secret) == cid


def test_token_wrong_secret_rejected() -> None:
    token = make_token("ws_CO_1", secret="a")
    assert parse_token(token, secret="b") is None


def test_token_tampered_payload_rejected() -> None:
    token = make_token("ws_CO_1", secret="s")
    bad = token[:-2] + "AA"
    assert parse_token(bad, secret="s") is None


def test_token_garbage_input_rejected() -> None:
    assert parse_token("not-a-token", secret="s") is None
    assert parse_token("$$$", secret="s") is None


def test_callback_url_shape() -> None:
    url = callback_url("ws_CO_1", base_url="https://api.example.com/", secret="s")
    assert url.startswith("https://api.example.com/webhooks/mpesa/stk/")
    token = url.rsplit("/", 1)[-1]
    assert parse_token(token, secret="s") == "ws_CO_1"
