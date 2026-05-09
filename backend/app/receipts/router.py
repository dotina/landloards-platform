"""HTTP routes for receipts + per-tenant statements."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import db_session
from app.auth.deps import require_landlord, require_tenant
from app.invoices.models import Invoice
from app.leases.models import Lease
from app.payments.models import Payment, PaymentStatus
from app.properties.models import Property, Unit
from app.receipts.service import (
    ReceiptData,
    StatementData,
    StatementRow,
    render_receipt_pdf,
    render_statement_pdf,
)
from app.tenants.models import Tenant
from app.tenants.service import get_tenant_by_user_id
from app.users.models import User


async def _resolve_payment_visible_to(
    db: AsyncSession, *, payment_id: uuid.UUID, user: User
) -> tuple[Payment, Tenant, User, Unit | None, Property | None, Invoice | None]:
    stmt = (
        select(Payment, Tenant, User, Invoice, Lease, Unit, Property)
        .join(Tenant, Tenant.id == Payment.tenant_id)
        .join(User, User.id == Tenant.user_id)
        .join(Invoice, Invoice.id == Payment.invoice_id, isouter=True)
        .join(Lease, Lease.id == Invoice.lease_id, isouter=True)
        .join(Unit, Unit.id == Lease.unit_id, isouter=True)
        .join(Property, Property.id == Unit.property_id, isouter=True)
        .where(Payment.id == payment_id)
    )
    row = (await db.execute(stmt)).first()
    if row is None:
        raise HTTPException(status_code=404, detail="payment not found")
    payment, tenant, tenant_user, invoice, _lease, unit, prop = row
    return payment, tenant, tenant_user, unit, prop, invoice


router = APIRouter(prefix="/payments", tags=["receipts"])


@router.get("/{payment_id}/receipt.pdf")
async def receipt_pdf(
    payment_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> Response:
    payment, tenant, tenant_user, unit, prop, invoice = await _resolve_payment_visible_to(
        db, payment_id=payment_id, user=user
    )

    me = await get_tenant_by_user_id(db, user_id=user.id)
    if me is None or tenant.id != me.id:
        raise HTTPException(status_code=404, detail="payment not found")

    if payment.status != PaymentStatus.SUCCESS:
        raise HTTPException(status_code=400, detail="payment is not in SUCCESS status")

    period_label = invoice.period_start.isoformat() if invoice else ""
    landlord_name = "Landloads"
    if prop is not None:
        landlord_user = await db.get(User, prop.landlord_id)
        if landlord_user is not None:
            landlord_name = landlord_user.name

    pdf = render_receipt_pdf(
        ReceiptData(
            receipt_no=str(payment.id)[:8].upper(),
            paid_at=payment.created_at or datetime.now(tz=timezone.utc),
            landlord_name=landlord_name,
            tenant_name=tenant_user.name,
            unit_label=unit.label if unit else "—",
            invoice_period_start=period_label,
            amount=payment.amount,
            channel=payment.channel.value,
            mpesa_receipt=payment.mpesa_receipt,
        )
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="receipt-{payment.id}.pdf"',
        },
    )


admin_router = APIRouter(prefix="/admin", tags=["receipts-admin"])


async def _build_statement(
    db: AsyncSession, *, tenant: Tenant, tenant_user: User, landlord_label: str
) -> bytes:
    invoices = (
        await db.execute(
            select(Invoice)
            .join(Lease, Lease.id == Invoice.lease_id)
            .where(Lease.tenant_id == tenant.id)
            .order_by(Invoice.period_start.asc())
        )
    ).scalars().all()
    payments = (
        await db.execute(
            select(Payment)
            .where(Payment.tenant_id == tenant.id, Payment.status == PaymentStatus.SUCCESS)
            .order_by(Payment.created_at.asc())
        )
    ).scalars().all()

    timeline: list[tuple[str, str, Decimal, Decimal]] = []  # (date, desc, debit, credit)
    for inv in invoices:
        timeline.append(
            (
                inv.period_start.isoformat(),
                f"Invoice {inv.id.hex[:8]} ({inv.period_start.isoformat()})",
                inv.amount + inv.late_fee_accrued,
                Decimal("0"),
            )
        )
    for p in payments:
        timeline.append(
            (
                (p.created_at or datetime.now(tz=timezone.utc)).date().isoformat(),
                f"Payment {p.id.hex[:8]} ({p.channel.value})",
                Decimal("0"),
                p.amount,
            )
        )
    timeline.sort(key=lambda t: t[0])

    rows: list[StatementRow] = []
    bal = Decimal("0")
    for when, desc, debit, credit in timeline:
        bal += debit - credit
        rows.append(StatementRow(when=when, description=desc, debit=debit, credit=credit, balance=bal))

    return render_statement_pdf(
        StatementData(
            landlord_name=landlord_label,
            tenant_name=tenant_user.name,
            period_label="All transactions",
            rows=rows,
        )
    )


@admin_router.get("/tenants/{tenant_id}/statement.pdf")
async def admin_statement(
    tenant_id: uuid.UUID,
    db: Annotated[AsyncSession, Depends(db_session)],
    landlord: Annotated[User, Depends(require_landlord)],
) -> Response:
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant not found")
    user = await db.get(User, tenant.user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="tenant user not found")

    pdf = await _build_statement(
        db, tenant=tenant, tenant_user=user, landlord_label=landlord.name
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="statement-{tenant.id}.pdf"',
        },
    )


tenant_router = APIRouter(prefix="/tenant", tags=["receipts-tenant"])


@tenant_router.get("/me/statement.pdf")
async def my_statement(
    db: Annotated[AsyncSession, Depends(db_session)],
    user: Annotated[User, Depends(require_tenant)],
) -> Response:
    tenant = await get_tenant_by_user_id(db, user_id=user.id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="tenant profile not found")
    pdf = await _build_statement(
        db, tenant=tenant, tenant_user=user, landlord_label="Your landlord"
    )
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="my-statement.pdf"',
        },
    )
