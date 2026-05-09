"""Single import that pulls in every ORM model so Alembic sees them.

Importing this module side-effects-registers every Mapped class with
`Base.metadata`, which is what `target_metadata` in alembic/env.py points at.
"""
from __future__ import annotations

from app.audit.models import AuditEvent  # noqa: F401
from app.invoices.models import Invoice  # noqa: F401
from app.leases.models import Lease  # noqa: F401
from app.notifications.models import NotificationLog  # noqa: F401
from app.payments.c2b_models import UnmatchedC2B  # noqa: F401
from app.payments.models import Payment  # noqa: F401
from app.plans.models import PaymentPlan  # noqa: F401
from app.properties.models import Property, Unit  # noqa: F401
from app.tenants.models import Tenant  # noqa: F401
from app.users.models import User  # noqa: F401
