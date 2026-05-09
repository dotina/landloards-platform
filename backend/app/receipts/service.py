"""Receipt + statement PDF rendering using reportlab.

Pure functions: take dataclasses, return ``bytes``. No DB calls live here so
the router can compose results from any layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass(frozen=True, slots=True)
class ReceiptData:
    receipt_no: str
    paid_at: datetime
    landlord_name: str
    tenant_name: str
    unit_label: str
    invoice_period_start: str  # ISO date
    amount: Decimal
    channel: str
    mpesa_receipt: str | None
    branding_color: str = "#0f766e"


@dataclass(frozen=True, slots=True)
class StatementRow:
    when: str  # ISO date
    description: str
    debit: Decimal = Decimal("0")
    credit: Decimal = Decimal("0")
    balance: Decimal = Decimal("0")


@dataclass(frozen=True, slots=True)
class StatementData:
    landlord_name: str
    tenant_name: str
    period_label: str
    rows: list[StatementRow] = field(default_factory=list)
    branding_color: str = "#0f766e"


def _kes(amount: Decimal) -> str:
    return f"KES {amount:,.2f}"


def render_receipt_pdf(data: ReceiptData) -> bytes:
    """Render a one-page receipt PDF and return its bytes."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        textColor=colors.HexColor(data.branding_color),
    )
    body_style = styles["BodyText"]

    story: list = [
        Paragraph(f"<b>{data.landlord_name}</b>", title_style),
        Paragraph("Rent receipt", styles["Heading2"]),
        Spacer(1, 6),
        Paragraph(f"Receipt #: <b>{data.receipt_no}</b>", body_style),
        Paragraph(f"Date: {data.paid_at.strftime('%Y-%m-%d %H:%M')}", body_style),
        Spacer(1, 12),
    ]

    rows = [
        ["Tenant", data.tenant_name],
        ["Unit", data.unit_label],
        ["Period", data.invoice_period_start],
        ["Channel", data.channel.upper()],
    ]
    if data.mpesa_receipt:
        rows.append(["M-Pesa receipt", data.mpesa_receipt])
    rows.append(["Amount paid", _kes(data.amount)])

    tbl = Table(rows, colWidths=[40 * mm, 100 * mm])
    tbl.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor(data.branding_color)),
                ("TEXTCOLOR", (0, -1), (-1, -1), colors.whitesmoke),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(tbl)
    story.append(Spacer(1, 12))
    story.append(
        Paragraph(
            "<i>Thank you for your payment. Keep this receipt for your records.</i>",
            body_style,
        )
    )

    doc.build(story)
    return buf.getvalue()


def render_statement_pdf(data: StatementData) -> bytes:
    """Render a per-tenant ledger statement."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm,
        topMargin=15 * mm, bottomMargin=15 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        textColor=colors.HexColor(data.branding_color),
    )

    story: list = [
        Paragraph(f"<b>{data.landlord_name}</b>", title_style),
        Paragraph(f"Statement for {data.tenant_name}", styles["Heading2"]),
        Paragraph(data.period_label, styles["BodyText"]),
        Spacer(1, 12),
    ]

    table_rows = [["Date", "Description", "Debit", "Credit", "Balance"]]
    for r in data.rows:
        table_rows.append(
            [
                r.when,
                r.description,
                _kes(r.debit) if r.debit else "",
                _kes(r.credit) if r.credit else "",
                _kes(r.balance),
            ]
        )

    tbl = Table(
        table_rows,
        colWidths=[25 * mm, 75 * mm, 25 * mm, 25 * mm, 30 * mm],
        repeatRows=1,
    )
    tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(data.branding_color)),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
                ("BOX", (0, 0), (-1, -1), 0.4, colors.grey),
            ]
        )
    )
    story.append(tbl)
    doc.build(story)
    return buf.getvalue()
