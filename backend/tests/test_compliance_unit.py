"""Compliance route smoke tests."""
from __future__ import annotations


def test_app_router_has_compliance_routes() -> None:
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/me/export" in paths
    assert "/me/privacy-notice" in paths


def test_privacy_notice_payload_shape() -> None:
    import asyncio

    from app.compliance.router import privacy_notice

    out = asyncio.run(privacy_notice())
    assert "version" in out
    assert "retention" in out
    assert isinstance(out["data_we_collect"], list)
    assert isinstance(out["your_rights"], list)
