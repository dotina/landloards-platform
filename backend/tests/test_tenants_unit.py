"""Unit-level tests for tenants + KYC."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.tenants.schemas import KycDecisionRequest, NextOfKin, TenantUpdateProfile


def test_next_of_kin_required_fields() -> None:
    with pytest.raises(ValidationError):
        NextOfKin(name="", relationship="brother", phone="0712345678")


def test_kyc_decision_requires_known_action() -> None:
    with pytest.raises(ValidationError):
        KycDecisionRequest(action="maybe")


def test_tenant_update_profile_partial_ok() -> None:
    body = TenantUpdateProfile(employer="Acme")
    assert body.employer == "Acme"
    assert body.next_of_kin is None


def test_app_router_has_kyc_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/tenant/me" in paths
    assert "/tenant/kyc/upload" in paths
    assert "/admin/tenants" in paths
    assert "/admin/tenants/{tenant_id}" in paths
    assert "/admin/tenants/{tenant_id}/kyc/url" in paths
    assert "/admin/tenants/{tenant_id}/kyc/decision" in paths
