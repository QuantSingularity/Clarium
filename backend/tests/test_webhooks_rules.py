"""Tests for webhooks and jurisdiction rule engine."""

import pytest

# ── Webhook Tests ─────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_register_webhook(client):
    r = await client.post(
        "/webhooks/",
        json={
            "url": "https://example.com/hook",
            "secret": "test-secret-key",
            "events": ["kyc.verified", "kyc.rejected"],
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["url"] == "https://example.com/hook"
    assert data["is_active"] is True
    assert "kyc.verified" in data["events"]


@pytest.mark.asyncio
async def test_list_webhooks(client):
    await client.post(
        "/webhooks/",
        json={
            "url": "https://app.example.com/events",
            "events": ["*"],
        },
    )
    r = await client.get("/webhooks/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert len(r.json()) >= 1


@pytest.mark.asyncio
async def test_delete_webhook(client):
    create = await client.post(
        "/webhooks/",
        json={
            "url": "https://delete-me.example.com/hook",
            "events": ["*"],
        },
    )
    wh_id = create.json()["id"]

    r = await client.delete(f"/webhooks/{wh_id}")
    assert r.status_code == 204

    # Confirm deleted
    r2 = await client.get("/webhooks/")
    ids = [w["id"] for w in r2.json()]
    assert wh_id not in ids


@pytest.mark.asyncio
async def test_webhook_deliveries_empty(client):
    create = await client.post(
        "/webhooks/",
        json={
            "url": "https://deliveries.example.com/hook",
            "events": ["kyc.verified"],
        },
    )
    wh_id = create.json()["id"]
    r = await client.get(f"/webhooks/{wh_id}/deliveries")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_webhook_404(client):
    r = await client.delete("/webhooks/99999")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_webhook_signing():
    """HMAC-SHA256 signature must be correct and reproducible."""
    import hashlib
    import hmac
    import json

    from src.services.webhook_service import _sign_payload

    secret = "my-webhook-secret"
    payload = {"event": "kyc.verified", "data": {"user_id": "u123"}}
    sig = _sign_payload(secret, payload)

    # Verify manually
    body = json.dumps(payload, sort_keys=True).encode()
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    assert sig == expected
    assert len(sig) == 64


@pytest.mark.asyncio
async def test_webhook_queuing(db):
    """queue_event must create delivery records for matching webhooks."""
    from sqlalchemy import select
    from src.models import WebhookDelivery, WebhookRegistration
    from src.services.webhook_service import queue_event

    # Register a webhook that listens to kyc.verified
    wh = WebhookRegistration(
        url="https://queue-test.example.com/hook",
        secret="secret",
        events=["kyc.verified"],
    )
    db.add(wh)
    await db.flush()

    count = await queue_event(db, "kyc.verified", {"user_id": "u_queue"})
    assert count >= 1

    # Check a delivery record was created
    result = await db.execute(
        select(WebhookDelivery).where(
            WebhookDelivery.webhook_id == wh.id,
            WebhookDelivery.event_type == "kyc.verified",
        )
    )
    deliveries = result.scalars().all()
    assert len(deliveries) >= 1
    assert deliveries[0].status == "pending"


# ── Rules Tests ───────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_rules_list_jurisdictions(client):
    r = await client.get("/rules/")
    assert r.status_code == 200
    data = r.json()
    assert "jurisdictions" in data
    # Should have loaded US, GB, EU, SG, AE
    for code in ["US", "GB", "EU", "SG", "AE"]:
        assert code in data["jurisdictions"]


@pytest.mark.asyncio
async def test_rules_get_us(client):
    r = await client.get("/rules/US")
    assert r.status_code == 200
    data = r.json()
    assert data["jurisdiction"] == "US"
    assert "transaction_limits" in data["rules"]
    assert "age_gate" in data["rules"]
    assert "kyc_tiers" in data["rules"]
    assert "required_disclosures" in data["rules"]


@pytest.mark.asyncio
async def test_rules_unknown_jurisdiction(client):
    r = await client.get("/rules/ZZ")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_rules_transaction_check_allowed(client):
    r = await client.post(
        "/rules/check/transaction",
        json={
            "jurisdiction": "US",
            "amount": 500.0,
            "currency": "USD",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["allowed"] is True
    assert data["kyc_tier"] == "basic"


@pytest.mark.asyncio
async def test_rules_transaction_check_blocked(client):
    r = await client.post(
        "/rules/check/transaction",
        json={
            "jurisdiction": "US",
            "amount": 999999.0,
            "currency": "USD",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["allowed"] is False
    assert "limit" in data


@pytest.mark.asyncio
async def test_rules_age_check_pass(client):
    r = await client.post(
        "/rules/check/age",
        json={
            "jurisdiction": "US",
            "age_years": 25.0,
        },
    )
    assert r.status_code == 200
    assert r.json()["allowed"] is True


@pytest.mark.asyncio
async def test_rules_age_check_fail(client):
    r = await client.post(
        "/rules/check/age",
        json={
            "jurisdiction": "US",
            "age_years": 16.0,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["allowed"] is False
    assert data["min_age"] == 18


@pytest.mark.asyncio
async def test_rules_kyc_tier_basic(client):
    from src.services.rule_engine import get_rule_engine

    engine = get_rule_engine()
    tier = engine.get_kyc_tier("US", 50.0)
    assert tier == "basic"


@pytest.mark.asyncio
async def test_rules_kyc_tier_enhanced(client):
    from src.services.rule_engine import get_rule_engine

    engine = get_rule_engine()
    tier = engine.get_kyc_tier("US", 15000.0)
    assert tier == "enhanced"


@pytest.mark.asyncio
async def test_rules_disclosures(client):
    from src.services.rule_engine import get_rule_engine

    engine = get_rule_engine()
    disclosures = engine.get_disclosures("GB")
    assert isinstance(disclosures, list)
    assert len(disclosures) > 0
    assert any("FCA" in d for d in disclosures)
