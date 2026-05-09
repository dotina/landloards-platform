"""User: auth principal. role ∈ {landlord, tenant, admin}."""
from __future__ import annotations

import enum

from sqlalchemy import Enum as SAEnum
from sqlalchemy import LargeBinary, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.models import Base, IdMixin, TimestampMixin


class UserRole(enum.StrEnum):
    LANDLORD = "landlord"
    TENANT = "tenant"
    ADMIN = "admin"


class User(IdMixin, TimestampMixin, Base):
    """Authentication principal."""

    __tablename__ = "users"

    phone: Mapped[str] = mapped_column(String(20), unique=True, nullable=False, index=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        SAEnum(UserRole, name="user_role", values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )

    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_verified: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Encrypted PII per design §3.3 — pgcrypto pgp_sym_encrypt at the service layer.
    id_number_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    kra_pin_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)

    # Short opaque code used as M-Pesa Paybill account-reference (Phase 9 lookup).
    tenant_code: Mapped[str | None] = mapped_column(String(8), unique=True, index=True)
