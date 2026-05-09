"""Unit-level tests for Properties + Units schemas + a small smoke."""
from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.properties.schemas import PropertyCreate, UnitCreate


def test_unit_due_day_must_be_within_1_28() -> None:
    with pytest.raises(ValidationError):
        UnitCreate(
            label="A1",
            rent_amount=Decimal("25000"),
            deposit_amount=Decimal("25000"),
            due_day_of_month=29,
        )
    with pytest.raises(ValidationError):
        UnitCreate(
            label="A1",
            rent_amount=Decimal("25000"),
            deposit_amount=Decimal("25000"),
            due_day_of_month=0,
        )


def test_unit_amounts_must_be_non_negative() -> None:
    with pytest.raises(ValidationError):
        UnitCreate(
            label="A1",
            rent_amount=Decimal("-1"),
            deposit_amount=Decimal("0"),
        )


def test_property_name_and_address_required() -> None:
    with pytest.raises(ValidationError):
        PropertyCreate(name="", address="ok")
    with pytest.raises(ValidationError):
        PropertyCreate(name="ok", address="")


def test_app_router_has_properties_routes() -> None:
    """Smoke: app should expose the property routes once create_app() runs."""
    from app.main import create_app

    app = create_app()
    paths = {r.path for r in app.routes}
    assert "/properties" in paths
    assert "/properties/{property_id}" in paths
    assert "/properties/{property_id}/units" in paths
    assert "/properties/{property_id}/photo" in paths
    assert "/units/{unit_id}" in paths
