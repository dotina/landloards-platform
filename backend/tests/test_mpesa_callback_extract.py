"""Pure-unit tests for the STK callback parser."""
from __future__ import annotations

from app.payments.service import _extract_callback_fields


def test_extract_success_envelope() -> None:
    body = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "m-1",
                "CheckoutRequestID": "ws_CO_1",
                "ResultCode": 0,
                "ResultDesc": "OK",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 100.0},
                        {"Name": "MpesaReceiptNumber", "Value": "QXX123"},
                        {"Name": "TransactionDate", "Value": 20260509120000},
                        {"Name": "PhoneNumber", "Value": 254712345678},
                    ]
                },
            }
        }
    }
    cid, code, items = _extract_callback_fields(body)
    assert cid == "ws_CO_1"
    assert code == 0
    assert items["MpesaReceiptNumber"] == "QXX123"


def test_extract_failure_envelope() -> None:
    body = {
        "Body": {
            "stkCallback": {
                "CheckoutRequestID": "ws_CO_2",
                "ResultCode": 1032,
                "ResultDesc": "Cancelled by user",
            }
        }
    }
    cid, code, items = _extract_callback_fields(body)
    assert cid == "ws_CO_2"
    assert code == 1032
    assert items == {}


def test_extract_missing_envelope_safe() -> None:
    cid, code, items = _extract_callback_fields({})
    assert cid == ""
    assert code == 1
    assert items == {}
