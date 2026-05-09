"""Jinja2 templates for notifications.

Each entry is a small inline string template; we keep them in code for now
because they are short and locale-stable (English-only MVP per design §1.3).
The map is exhaustive: every name listed here is the canonical template id
referenced from the rest of the codebase.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jinja2 import Environment, StrictUndefined


@dataclass(frozen=True, slots=True)
class Template:
    body: str  # SMS body / email plain text
    subject: str = ""  # email-only


_RAW: dict[str, Template] = {
    "tenant_invite": Template(
        subject="You've been invited to Landloads",
        body=(
            "Hi {{ name }}, your landlord has invited you to Landloads. "
            "Open this link to set up your account: {{ accept_url }}"
        ),
    ),
    "otp": Template(
        body="Your Landloads code is {{ code }}. Valid for {{ ttl_min }} minutes.",
    ),
    "rent_reminder_t3": Template(
        body=(
            "Reminder: KES {{ amount }} rent for {{ unit_label }} is due on "
            "{{ due_date }} (3 days). Pay with M-Pesa Paybill {{ paybill }} ref {{ tenant_code }}."
        ),
    ),
    "rent_reminder_t0": Template(
        body=(
            "Today: KES {{ amount }} rent for {{ unit_label }} is due. "
            "Pay with M-Pesa Paybill {{ paybill }} ref {{ tenant_code }}."
        ),
    ),
    "rent_overdue_t3": Template(
        body=(
            "OVERDUE 3d: KES {{ amount }} rent for {{ unit_label }} (since {{ due_date }}). "
            "Late fee applies."
        ),
    ),
    "rent_overdue_t7": Template(
        body=(
            "OVERDUE 7d: KES {{ amount }} for {{ unit_label }}. "
            "Pay or request a payment plan."
        ),
    ),
    "rent_overdue_t14": Template(
        body=(
            "URGENT: KES {{ amount }} for {{ unit_label }} is 14 days overdue. "
            "Contact your landlord."
        ),
    ),
    "payment_received": Template(
        subject="Receipt for your Landloads payment",
        body=(
            "Received KES {{ amount }} for {{ unit_label }} on {{ paid_at }}. "
            "Receipt: {{ receipt_no }}."
        ),
    ),
    "plan_pending": Template(
        subject="Payment plan requested",
        body="Tenant {{ tenant_name }} requested a plan on invoice {{ invoice_no }}.",
    ),
    "plan_approved": Template(
        subject="Payment plan approved",
        body=(
            "Your plan on invoice {{ invoice_no }} is approved. Next installment: "
            "KES {{ next_amount }} on {{ next_date }}."
        ),
    ),
    "plan_defaulted": Template(
        subject="Payment plan defaulted",
        body=(
            "Your plan on invoice {{ invoice_no }} has defaulted (missed installment). "
            "Late fees resume."
        ),
    ),
}

_env = Environment(undefined=StrictUndefined, autoescape=False)


def render(template: str, context: dict[str, Any]) -> tuple[str, str]:
    """Render a template; return ``(body, subject)``.

    Raises ``KeyError`` if the template name is unknown. Raises Jinja
    ``UndefinedError`` if a context variable is missing.
    """
    tpl = _RAW[template]
    body = _env.from_string(tpl.body).render(**context)
    subject = _env.from_string(tpl.subject).render(**context) if tpl.subject else ""
    return body, subject


def known_templates() -> set[str]:
    return set(_RAW)
