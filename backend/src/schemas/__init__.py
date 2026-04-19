from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ── KYC ──────────────────────────────────────────────────────────────────────


class KYCStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    VERIFIED = "verified"
    REJECTED = "rejected"
    REVIEW = "review"


class KYCSubmitRequest(BaseModel):
    user_id: str
    full_name: str
    date_of_birth: date
    nationality: str = Field(..., min_length=2, max_length=3)
    document_type: str = Field(..., pattern="^(passport|national_id|driving_license)$")
    document_number: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "user_001",
                "full_name": "Alice Johnson",
                "date_of_birth": "1990-05-15",
                "nationality": "US",
                "document_type": "passport",
                "document_number": "A12345678",
            }
        }


class KYCStatusResponse(BaseModel):
    user_id: str
    status: KYCStatus
    identity_score: Optional[float]
    ocr_confidence: Optional[float]
    submitted_at: datetime
    updated_at: datetime
    verified_at: Optional[datetime]
    rejected_at: Optional[datetime]
    reviewer_notes: Optional[str]

    class Config:
        from_attributes = True


class KYCReviewRequest(BaseModel):
    status: KYCStatus
    reviewer_notes: Optional[str] = None


# ── AML ──────────────────────────────────────────────────────────────────────


class AMLCheckRequest(BaseModel):
    transaction_id: str
    user_id: Optional[str] = None
    amount: float = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    source_country: Optional[str] = None
    destination_country: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "transaction_id": "txn_abc123",
                "user_id": "user_001",
                "amount": 15000.00,
                "currency": "USD",
                "source_country": "US",
                "destination_country": "RU",
            }
        }


class AMLCheckResponse(BaseModel):
    transaction_id: str
    flagged: bool
    risk_score: float
    flag_reasons: List[str]
    pep_match: bool
    status: str
    checked_at: datetime

    class Config:
        from_attributes = True


# ── Audit ─────────────────────────────────────────────────────────────────────


class AuditEventResponse(BaseModel):
    id: int
    entity_type: str
    entity_id: str
    event_type: str
    actor_id: Optional[str]
    payload: Dict[str, Any]
    this_hash: str
    prev_hash: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Webhooks ──────────────────────────────────────────────────────────────────


class WebhookCreateRequest(BaseModel):
    url: str
    secret: Optional[str] = None
    events: List[str] = Field(default=["*"])

    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://myapp.example.com/hooks/clarium",
                "secret": "my-webhook-secret",
                "events": ["kyc.verified", "kyc.rejected", "aml.flagged"],
            }
        }


class WebhookResponse(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookDeliveryResponse(BaseModel):
    id: int
    webhook_id: int
    event_type: str
    status: str
    attempts: int
    response_code: Optional[int]
    delivered_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


# ── Rules ─────────────────────────────────────────────────────────────────────


class JurisdictionRulesResponse(BaseModel):
    jurisdiction: str
    rules: Dict[str, Any]
    effective_date: Optional[str]
    last_updated: Optional[str]
