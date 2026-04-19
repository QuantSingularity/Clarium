"""Tests for KYC pipeline."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_kyc_submit_success(client):
    r = await client.post(
        "/kyc/submit",
        json={
            "user_id": "test_user_001",
            "full_name": "Alice Johnson",
            "date_of_birth": "1990-05-15",
            "nationality": "US",
            "document_type": "passport",
            "document_number": "A12345678",
        },
    )
    assert r.status_code == 201
    data = r.json()
    assert data["user_id"] == "test_user_001"
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_kyc_duplicate_rejected(client):
    payload = {
        "user_id": "dup_user",
        "full_name": "Bob Smith",
        "date_of_birth": "1985-03-20",
        "nationality": "GB",
        "document_type": "national_id",
        "document_number": "B98765432",
    }
    await client.post("/kyc/submit", json=payload)
    r = await client.post("/kyc/submit", json=payload)
    assert r.status_code == 409


@pytest.mark.asyncio
async def test_kyc_status_not_found(client):
    r = await client.get("/kyc/status/nonexistent_user")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_kyc_status_found(client):
    await client.post(
        "/kyc/submit",
        json={
            "user_id": "status_test_user",
            "full_name": "Carol White",
            "date_of_birth": "1992-08-10",
            "nationality": "US",
            "document_type": "passport",
            "document_number": "C11223344",
        },
    )
    r = await client.get("/kyc/status/status_test_user")
    assert r.status_code == 200
    assert r.json()["user_id"] == "status_test_user"
    assert r.json()["status"] == "pending"


@pytest.mark.asyncio
async def test_kyc_queue(client):
    r = await client.get("/kyc/queue")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.asyncio
async def test_kyc_invalid_document_type(client):
    r = await client.post(
        "/kyc/submit",
        json={
            "user_id": "invalid_doc_user",
            "full_name": "Dave Brown",
            "date_of_birth": "1988-01-01",
            "nationality": "US",
            "document_type": "selfie",  # invalid
            "document_number": "D00000001",
        },
    )
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_kyc_underage_rejected(client):
    """Users under 18 should get a low identity score → rejected status."""
    from datetime import date

    from src.services.kyc_service import compute_identity_score

    # Age 15 - should fail age check component
    dob = date(date.today().year - 15, 1, 1)
    score, breakdown = compute_identity_score(
        ocr_result={
            "confidence": 0.99,
            "extracted_name": "Minor User",
            "extracted_document_number": "M0001",
        },
        submitted_name="Minor User",
        submitted_number="M0001",
        date_of_birth=dob,
        nationality="US",
    )
    # Age check contributes 0 → total score drops
    assert breakdown["age_check"] == 0.0
    assert score < 0.90  # Even with perfect OCR, age fails the 10% component
