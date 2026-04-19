"""Tests for audit trail and hash-chain integrity."""

import pytest


@pytest.mark.asyncio
async def test_audit_trail_created_on_kyc(client):
    """KYC submission must create an audit event."""
    await client.post(
        "/kyc/submit",
        json={
            "user_id": "audit_kyc_user",
            "full_name": "Audit Test User",
            "date_of_birth": "1990-01-01",
            "nationality": "US",
            "document_type": "passport",
            "document_number": "AU1234567",
        },
    )
    r = await client.get("/audit/trail/audit_kyc_user")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1
    assert any(e["event_type"] == "kyc.submitted" for e in events)


@pytest.mark.asyncio
async def test_audit_trail_created_on_aml(client):
    """AML check must create an audit event."""
    await client.post(
        "/aml/check",
        json={
            "transaction_id": "txn_audit_001",
            "amount": 500.0,
            "currency": "USD",
        },
    )
    r = await client.get("/audit/trail/txn_audit_001")
    assert r.status_code == 200
    events = r.json()
    assert len(events) >= 1
    assert any("aml." in e["event_type"] for e in events)


@pytest.mark.asyncio
async def test_audit_event_has_hash(client):
    """Every audit event must have a this_hash field."""
    await client.post(
        "/kyc/submit",
        json={
            "user_id": "hash_test_user",
            "full_name": "Hash User",
            "date_of_birth": "1988-06-15",
            "nationality": "GB",
            "document_type": "national_id",
            "document_number": "HT9876543",
        },
    )
    r = await client.get("/audit/trail/hash_test_user")
    events = r.json()
    assert len(events) > 0
    for event in events:
        assert "this_hash" in event
        assert len(event["this_hash"]) == 64  # SHA-256 hex = 64 chars


@pytest.mark.asyncio
async def test_audit_chain_is_valid(client):
    """Chain verification endpoint must report valid."""
    r = await client.get("/audit/verify")
    assert r.status_code == 200
    data = r.json()
    assert "valid" in data
    assert data["valid"] is True
    assert "checked" in data
    assert data["violations"] == []


@pytest.mark.asyncio
async def test_audit_hash_chaining(db):
    """Consecutive events must chain: event N's prev_hash == event N-1's this_hash."""
    from src.services.audit_service import log_event

    e1 = await log_event(db, "kyc", "chain_user", "kyc.submitted", {"step": 1})
    e2 = await log_event(db, "kyc", "chain_user", "kyc.processing", {"step": 2})
    e3 = await log_event(db, "kyc", "chain_user", "kyc.verified", {"step": 3})

    assert e2.prev_hash == e1.this_hash
    assert e3.prev_hash == e2.this_hash
    assert e1.this_hash != e2.this_hash
    assert e2.this_hash != e3.this_hash


@pytest.mark.asyncio
async def test_audit_hash_deterministic(db):
    """Same inputs must always produce the same hash."""
    from datetime import datetime, timezone

    from src.services.audit_service import _compute_hash

    ts = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    h1 = _compute_hash("kyc", "u1", "kyc.submitted", "actor", {"k": "v"}, ts, None)
    h2 = _compute_hash("kyc", "u1", "kyc.submitted", "actor", {"k": "v"}, ts, None)
    assert h1 == h2
    assert len(h1) == 64


@pytest.mark.asyncio
async def test_audit_recent_events(client):
    r = await client.get("/audit/recent?limit=10")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_audit_filter_by_entity_type(client):
    await client.post(
        "/kyc/submit",
        json={
            "user_id": "filter_type_user",
            "full_name": "Filter User",
            "date_of_birth": "1995-03-10",
            "nationality": "SG",
            "document_type": "passport",
            "document_number": "FT0011223",
        },
    )
    r = await client.get("/audit/trail/filter_type_user?entity_type=kyc")
    assert r.status_code == 200
    events = r.json()
    for e in events:
        assert e["entity_type"] == "kyc"
