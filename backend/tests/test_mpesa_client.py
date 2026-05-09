"""Daraja client tests — respx-mocked HTTP."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.payments.mpesa import client as daraja


@pytest.mark.asyncio
async def test_oauth_returns_token() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get(url__regex=r".*oauth.*generate.*").mock(
            return_value=httpx.Response(200, json={"access_token": "abc", "expires_in": "3599"})
        )
        token = await daraja.get_access_token()
        assert token == "abc"


@pytest.mark.asyncio
async def test_oauth_failure_raises() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get(url__regex=r".*oauth.*").mock(return_value=httpx.Response(401, text="nope"))
        with pytest.raises(daraja.DarajaError):
            await daraja.get_access_token()


@pytest.mark.asyncio
async def test_stk_push_round_trip() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get(url__regex=r".*oauth.*").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        mock.post(url__regex=r".*stkpush.*processrequest").mock(
            return_value=httpx.Response(
                200,
                json={
                    "MerchantRequestID": "m-1",
                    "CheckoutRequestID": "ws_CO_1",
                    "ResponseCode": "0",
                    "ResponseDescription": "ok",
                    "CustomerMessage": "Success",
                },
            )
        )
        result = await daraja.stk_push(
            phone="254712345678",
            amount=100,
            account_reference="ABC123",
            transaction_desc="Inv abcdef",
            callback_url="https://x/cb",
        )
        assert result.checkout_request_id == "ws_CO_1"


@pytest.mark.asyncio
async def test_stk_push_non_zero_response_code_raises() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get(url__regex=r".*oauth.*").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        mock.post(url__regex=r".*stkpush.*processrequest").mock(
            return_value=httpx.Response(200, json={"ResponseCode": "1", "errorMessage": "denied"})
        )
        with pytest.raises(daraja.DarajaError):
            await daraja.stk_push(
                phone="254712345678",
                amount=100,
                account_reference="ABC",
                transaction_desc="x",
                callback_url="https://x",
            )


@pytest.mark.asyncio
async def test_stk_query_returns_result_code() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.get(url__regex=r".*oauth.*").mock(
            return_value=httpx.Response(200, json={"access_token": "tok"})
        )
        mock.post(url__regex=r".*stkpushquery.*").mock(
            return_value=httpx.Response(200, json={"ResultCode": "0", "ResultDesc": "ok"})
        )
        r = await daraja.stk_query(checkout_request_id="ws_CO_1")
        assert r.result_code == "0"


@pytest.mark.asyncio
async def test_app_router_has_mpesa_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/payments/stk/initiate" in paths
    assert "/payments/stk/{checkout_request_id}" in paths
    assert "/admin/payments" in paths
    assert "/webhooks/mpesa/stk/{token}" in paths
