"""PDF rendering smoke tests."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from app.receipts.service import (
    ReceiptData,
    StatementData,
    StatementRow,
    render_receipt_pdf,
    render_statement_pdf,
)


def test_receipt_pdf_returns_pdf_bytes() -> None:
    data = ReceiptData(
        receipt_no="ABCD1234",
        paid_at=datetime(2026, 5, 9, 10, 30, tzinfo=timezone.utc),
        landlord_name="Acme Properties",
        tenant_name="Alice Wanjiku",
        unit_label="A1",
        invoice_period_start="2026-05-01",
        amount=Decimal("25000.00"),
        channel="mpesa_stk",
        mpesa_receipt="QXX123ABC",
    )
    pdf = render_receipt_pdf(data)
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_statement_pdf_with_no_rows() -> None:
    pdf = render_statement_pdf(
        StatementData(
            landlord_name="Acme",
            tenant_name="Alice",
            period_label="2026",
            rows=[],
        )
    )
    assert pdf.startswith(b"%PDF-")


def test_statement_pdf_with_rows() -> None:
    rows = [
        StatementRow(
            when="2026-05-01", description="Invoice", debit=Decimal("25000"), balance=Decimal("25000")
        ),
        StatementRow(
            when="2026-05-09", description="Payment", credit=Decimal("25000"), balance=Decimal("0")
        ),
    ]
    pdf = render_statement_pdf(
        StatementData(landlord_name="Acme", tenant_name="Alice", period_label="May", rows=rows)
    )
    assert pdf.startswith(b"%PDF-")


def test_app_router_has_receipt_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/payments/{payment_id}/receipt.pdf" in paths
    assert "/admin/tenants/{tenant_id}/statement.pdf" in paths
    assert "/tenant/me/statement.pdf" in paths
