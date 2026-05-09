"""Notifications: template render + provider HTTP shape (respx)."""
from __future__ import annotations

import httpx
import pytest
import respx

from app.notifications import templates
from app.notifications.providers.email_resend import EmailSendError, send_email
from app.notifications.providers.sms_at import SmsSendError, send_sms


def test_template_render_otp() -> None:
    body, subject = templates.render("otp", {"code": "123456", "ttl_min": 10})
    assert "123456" in body
    assert subject == ""


def test_template_render_unknown_raises() -> None:
    with pytest.raises(KeyError):
        templates.render("does_not_exist", {})


def test_template_render_missing_var_raises() -> None:
    from jinja2 import UndefinedError

    with pytest.raises(UndefinedError):
        templates.render("otp", {})  # missing code & ttl_min


def test_known_templates_match_design_set() -> None:
    expected = {
        "tenant_invite",
        "otp",
        "rent_reminder_t3",
        "rent_reminder_t0",
        "rent_overdue_t3",
        "rent_overdue_t7",
        "rent_overdue_t14",
        "payment_received",
        "plan_pending",
        "plan_approved",
        "plan_defaulted",
    }
    assert templates.known_templates() == expected


@pytest.mark.asyncio
async def test_send_sms_success() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.post(url__regex=r".*africastalking.*messaging").mock(
            return_value=httpx.Response(
                201,
                json={
                    "SMSMessageData": {
                        "Message": "Sent to 1/1 Total Cost: KES 1.0000",
                        "Recipients": [
                            {
                                "statusCode": 101,
                                "number": "+254700000000",
                                "status": "Success",
                                "cost": "KES 1.0000",
                                "messageId": "ATXid_abc123",
                            }
                        ],
                    }
                },
            )
        )
        result = await send_sms(phone="+254700000000", body="hi")
        assert result.provider_message_id == "ATXid_abc123"


@pytest.mark.asyncio
async def test_send_sms_provider_error_raises() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.post(url__regex=r".*messaging").mock(return_value=httpx.Response(401, text="nope"))
        with pytest.raises(SmsSendError):
            await send_sms(phone="+254700000000", body="hi")


@pytest.mark.asyncio
async def test_send_sms_no_recipients_raises() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.post(url__regex=r".*messaging").mock(
            return_value=httpx.Response(
                200, json={"SMSMessageData": {"Message": "ok", "Recipients": []}}
            )
        )
        with pytest.raises(SmsSendError):
            await send_sms(phone="+254700000000", body="hi")


@pytest.mark.asyncio
async def test_send_email_success() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.post(url__regex=r".*resend.com/emails").mock(
            return_value=httpx.Response(200, json={"id": "re_abc"})
        )
        r = await send_email(to="alice@example.com", subject="hi", text="hello")
        assert r.provider_message_id == "re_abc"


@pytest.mark.asyncio
async def test_send_email_failure_raises() -> None:
    with respx.mock(assert_all_called=True) as mock:
        mock.post(url__regex=r".*emails").mock(return_value=httpx.Response(500, text="boom"))
        with pytest.raises(EmailSendError):
            await send_email(to="alice@example.com", subject="hi", text="hello")


def test_app_router_has_notifications_log() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/admin/notifications" in paths
