"""
Rules Router
GET /rules/{jurisdiction}         - Get rules for a jurisdiction
GET /rules/                       - List all loaded jurisdictions
POST /rules/check/transaction     - Check a transaction against jurisdiction rules
POST /rules/check/age             - Check age gate for jurisdiction
POST /rules/reload                - Hot-reload rules from disk (admin)
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..schemas import JurisdictionRulesResponse
from ..services.rule_engine import get_rule_engine

router = APIRouter()


class TransactionCheckRequest(BaseModel):
    jurisdiction: str
    amount: float
    currency: str = "USD"


class AgeCheckRequest(BaseModel):
    jurisdiction: str
    age_years: float


@router.get("/", summary="List all loaded jurisdictions")
async def list_jurisdictions():
    engine = get_rule_engine()
    return {"jurisdictions": engine.list_jurisdictions()}


@router.get("/{jurisdiction}", response_model=JurisdictionRulesResponse)
async def get_rules(jurisdiction: str):
    """Get the full rule set for a jurisdiction code (e.g. US, GB, SG)."""
    engine = get_rule_engine()
    rules = engine.get(jurisdiction)
    if not rules:
        raise HTTPException(404, f"No rules defined for jurisdiction '{jurisdiction}'")
    return JurisdictionRulesResponse(
        jurisdiction=jurisdiction.upper(),
        rules=rules,
        effective_date=rules.get("effective_date"),
        last_updated=rules.get("last_updated"),
    )


@router.post("/check/transaction")
async def check_transaction(body: TransactionCheckRequest):
    """Check whether a transaction amount is permitted under jurisdiction rules."""
    engine = get_rule_engine()
    result = engine.check_transaction_limit(
        body.jurisdiction, body.amount, body.currency
    )
    result["jurisdiction"] = body.jurisdiction.upper()
    result["amount"] = body.amount
    result["currency"] = body.currency
    result["kyc_tier"] = engine.get_kyc_tier(body.jurisdiction, body.amount)
    result["disclosures"] = engine.get_disclosures(body.jurisdiction)
    return result


@router.post("/check/age")
async def check_age(body: AgeCheckRequest):
    """Check whether a user meets the age gate for a jurisdiction."""
    engine = get_rule_engine()
    result = engine.check_age_gate(body.jurisdiction, body.age_years)
    result["jurisdiction"] = body.jurisdiction.upper()
    result["age_years"] = body.age_years
    return result


@router.post("/reload", status_code=200)
async def reload_rules():
    """Hot-reload jurisdiction rules from disk without restarting the service."""
    engine = get_rule_engine()
    engine.reload()
    return {
        "status": "reloaded",
        "jurisdictions": engine.list_jurisdictions(),
    }
