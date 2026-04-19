"""
Clarium KYC Service
===================
- Mock OCR: simulates document scanning and field extraction
- Identity scoring: composite score from OCR confidence, document validity, age check
- State machine: pending → processing → verified | rejected | review
"""

import hashlib
import logging
import random
from datetime import date
from typing import Any, Dict, Tuple

from ..config import settings

logger = logging.getLogger("clarium.kyc")

# ── Mock OCR ──────────────────────────────────────────────────────────────────


async def run_ocr(
    document_uri: str,
    document_type: str,
    full_name: str,
    document_number: str,
) -> Dict[str, Any]:
    """
    Mock OCR service.
    In production, replace with call to settings.ocr_service_url.
    Returns extracted fields and a confidence score.
    """
    if settings.ocr_service_url != "mock":
        import httpx

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                settings.ocr_service_url + "/ocr",
                json={
                    "document_uri": document_uri,
                    "document_type": document_type,
                },
            )
            resp.raise_for_status()
            return resp.json()

    # ── Deterministic mock (seed on document_number for repeatability) ──────
    seed = int(hashlib.md5(document_number.encode()).hexdigest(), 16) % 1000
    rng = random.Random(seed)

    confidence = rng.uniform(0.65, 0.99)

    # Simulate OCR extraction
    extracted_name = full_name if confidence > 0.75 else full_name[:-1] + "x"
    extracted_number = (
        document_number if confidence > 0.70 else document_number[:-2] + "XX"
    )

    return {
        "extracted_name": extracted_name,
        "extracted_document_number": extracted_number,
        "extracted_document_type": document_type,
        "confidence": round(confidence, 4),
        "fields_detected": ["name", "document_number", "document_type"],
        "provider": "mock-ocr-v1",
    }


# ── Identity Scoring ──────────────────────────────────────────────────────────


def compute_identity_score(
    ocr_result: Dict[str, Any],
    submitted_name: str,
    submitted_number: str,
    date_of_birth: date,
    nationality: str,
) -> Tuple[float, Dict[str, Any]]:
    """
    Compute composite identity verification score 0.0-1.0.
    Components:
      - OCR confidence (40%)
      - Name match (30%)
      - Document number match (20%)
      - Age check (10%) - must be 18+
    Returns (score, score_breakdown).
    """
    breakdown = {}

    # 1. OCR confidence (40%)
    ocr_conf = ocr_result.get("confidence", 0.0)
    breakdown["ocr_confidence"] = round(ocr_conf * 0.40, 4)

    # 2. Name similarity (30%)
    extracted_name = ocr_result.get("extracted_name", "")
    name_score = _name_similarity(submitted_name, extracted_name)
    breakdown["name_match"] = round(name_score * 0.30, 4)

    # 3. Document number match (20%)
    extracted_num = ocr_result.get("extracted_document_number", "")
    num_match = 1.0 if submitted_number.upper() == extracted_num.upper() else 0.3
    breakdown["document_number_match"] = round(num_match * 0.20, 4)

    # 4. Age check (10%) - must be 18+
    today = date.today()
    age_years = (today - date_of_birth).days / 365.25
    age_score = 1.0 if age_years >= 18 else 0.0
    breakdown["age_check"] = round(age_score * 0.10, 4)

    total = sum(breakdown.values())
    breakdown["total"] = round(total, 4)

    logger.debug(f"Identity score breakdown: {breakdown}")
    return round(total, 4), breakdown


def _name_similarity(a: str, b: str) -> float:
    """Simple token-level name similarity."""
    tokens_a = set(a.lower().split())
    tokens_b = set(b.lower().split())
    if not tokens_a or not tokens_b:
        return 0.0
    intersection = tokens_a & tokens_b
    union = tokens_a | tokens_b
    return len(intersection) / len(union)


# ── State Machine ─────────────────────────────────────────────────────────────

VALID_TRANSITIONS = {
    "pending": {"processing"},
    "processing": {"verified", "rejected", "review"},
    "review": {"verified", "rejected"},
    "verified": set(),
    "rejected": set(),
}


def is_valid_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


def determine_kyc_status(identity_score: float) -> str:
    """Map a score to a KYC status."""
    if identity_score >= settings.kyc_score_threshold_verified:
        return "verified"
    elif identity_score >= settings.kyc_score_threshold_review:
        return "review"
    else:
        return "rejected"
