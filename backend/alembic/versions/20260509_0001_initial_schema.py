"""initial_schema

Creates every table defined under app.* models and applies the
design-§3.2 invariants that SQLAlchemy metadata cannot express:

* `pgcrypto` extension (used for encrypted PII columns).
* Append-only grants on `audit_event` (revoke UPDATE/DELETE on the app role).

Partial unique indexes for payments idempotency are encoded on the
SQLAlchemy model via ``postgresql_where`` so ``metadata.create_all``
emits them automatically.

Revision ID: 20260509_0001
Revises: 8159f243f3fe
Create Date: 2026-05-09
"""

from __future__ import annotations

from collections.abc import Sequence

import app.core.all_models  # noqa: F401  side-effect: register all models
from alembic import op
from app.core.config import get_settings
from app.core.models import Base

revision: str = "20260509_0001"
down_revision: str | Sequence[str] | None = "8159f243f3fe"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create all tables, indexes, and apply audit grants."""
    bind = op.get_bind()
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    Base.metadata.create_all(bind=bind)

    # Design §3.2: app role on `audit_event` may only INSERT and SELECT.
    # We resolve the role from DATABASE_URL at migration time so dev/staging/prod
    # work without a hard-coded role name.
    db_url = get_settings().database_url
    role = db_url.rsplit("//", 1)[1].split(":", 1)[0]
    op.execute(f"REVOKE UPDATE, DELETE, TRUNCATE ON TABLE audit_event FROM {role}")
    op.execute(f"GRANT INSERT, SELECT ON TABLE audit_event TO {role}")


def downgrade() -> None:
    """Drop everything created in upgrade()."""
    bind = op.get_bind()
    Base.metadata.drop_all(bind=bind)
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
