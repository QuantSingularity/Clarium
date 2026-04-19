"""Tests for AML rule engine."""

import pytest


@pytest.mark.asyncio
async def test_aml_check_clear(client):
    r = await client.post(
        "/aml/check",
        json={
            "transaction_id": "txn_clear_001",
            "user_id": "user_safe",
            "amount": 500.0,
            "currency": "USD",
            "source_country": "US",
            "destination_country": "GB",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["transaction_id"] == "txn_clear_001"
    assert data["flagged"] is False
    assert data["status"] == "clear"
    assert data["risk_score"] < 0.70


@pytest.mark.asyncio
async def test_aml_check_amount_threshold(client):
    r = await client.post(
        "/aml/check",
        json={
            "transaction_id": "txn_large_001",
            "user_id": "user_big_spender",
            "amount": 25000.0,
            "currency": "USD",
            "source_country": "US",
            "destination_country": "US",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["flagged"] is True
    assert data["risk_score"] >= 0.40
    assert any("Amount" in r for r in data["flag_reasons"])


@pytest.mark.asyncio
async def test_aml_check_high_risk_country(client):
    r = await client.post(
        "/aml/check",
        json={
            "transaction_id": "txn_geo_001",
            "user_id": "user_geo",
            "amount": 100.0,
            "currency": "USD",
            "source_country": "KP",  # North Korea - 0.98 risk
            "destination_country": "US",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["flagged"] is True
    assert any("Geographic" in r for r in data["flag_reasons"])


@pytest.mark.asyncio
async def test_aml_list_flags(client):
    # Create a flagged transaction first
    await client.post(
        "/aml/check",
        json={
            "transaction_id": "txn_for_list",
            "amount": 50000.0,
            "currency": "USD",
            "source_country": "US",
            "destination_country": "US",
        },
    )
    r = await client.get("/aml/flags?flagged_only=true")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_aml_invalid_amount(client):
    r = await client.post(
        "/aml/check",
        json={
            "transaction_id": "txn_bad",
            "amount": -100.0,  # must be > 0
            "currency": "USD",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_aml_rule_engine_directly(db):
    """Test the AML service directly for all four rule branches."""
    from src.services.aml_service import run_aml_check

    # Amount trigger only
    risk, flagged, reasons, pep, _ = await run_aml_check(
        db, "txn_direct", None, 15000.0, "USD", "US", "US"
    )
    assert flagged is True
    assert any("Amount" in r for r in reasons)

    # Geo risk only (small amount, high-risk country)
    risk2, flagged2, reasons2, _, _ = await run_aml_check(
        db, "txn_geo_direct", None, 50.0, "USD", "IR", "US"
    )
    assert flagged2 is True
    assert any("Geographic" in r for r in reasons2)

    # Clean transaction
    risk3, flagged3, reasons3, _, _ = await run_aml_check(
        db, "txn_clean_direct", None, 100.0, "USD", "US", "GB"
    )
    assert flagged3 is False
    assert len(reasons3) == 0
