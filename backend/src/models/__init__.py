from datetime import datetime, timezone

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB

from .database import Base


def _now():
    return datetime.now(timezone.utc)


class KYCSubmission(Base):
    __tablename__ = "kyc_submissions"

    id = Column(Integer, primary_key=True)
    user_id = Column(String(256), unique=True, nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)
    full_name = Column(String(512))
    date_of_birth = Column(Date)
    nationality = Column(String(8))
    document_type = Column(String(64))
    document_number = Column(String(256))
    document_uri = Column(Text)
    ocr_raw = Column(JSONB)
    ocr_confidence = Column(Float)
    identity_score = Column(Float)
    reviewer_notes = Column(Text)
    submitted_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
    verified_at = Column(DateTime(timezone=True))
    rejected_at = Column(DateTime(timezone=True))


class AMLCheck(Base):
    __tablename__ = "aml_checks"

    id = Column(BigInteger, primary_key=True)
    transaction_id = Column(String(256), nullable=False, index=True)
    user_id = Column(String(256), index=True)
    amount = Column(Numeric(18, 4), nullable=False)
    currency = Column(String(8), nullable=False, default="USD")
    source_country = Column(String(8))
    destination_country = Column(String(8))
    risk_score = Column(Float, nullable=False, default=0.0)
    flagged = Column(Boolean, nullable=False, default=False, index=True)
    flag_reasons = Column(JSONB, default=list)
    pep_match = Column(Boolean, nullable=False, default=False)
    pep_match_details = Column(JSONB)
    status = Column(String(32), nullable=False, default="clear")
    checked_at = Column(DateTime(timezone=True), default=_now)
    reviewed_at = Column(DateTime(timezone=True))
    reviewer_id = Column(String(256))


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(BigInteger, primary_key=True)
    entity_type = Column(String(64), nullable=False)
    entity_id = Column(String(256), nullable=False)
    event_type = Column(String(128), nullable=False)
    actor_id = Column(String(256))
    payload = Column(JSONB, nullable=False, default=dict)
    ip_address = Column(String(45))  # store as string for simplicity
    prev_hash = Column(String(64))
    this_hash = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_now)


class WebhookRegistration(Base):
    __tablename__ = "webhook_registrations"

    id = Column(Integer, primary_key=True)
    url = Column(Text, nullable=False)
    secret = Column(String(256))
    events = Column(JSONB, nullable=False, default=lambda: ["*"])
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)


class WebhookDelivery(Base):
    __tablename__ = "webhook_deliveries"

    id = Column(BigInteger, primary_key=True)
    webhook_id = Column(Integer, nullable=False)
    event_type = Column(String(128), nullable=False)
    payload = Column(JSONB, nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    attempts = Column(Integer, nullable=False, default=0)
    response_code = Column(Integer)
    response_body = Column(Text)
    next_retry_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=_now)


class PEPEntry(Base):
    __tablename__ = "pep_list"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(512), nullable=False)
    aliases = Column(JSONB, default=list)
    country = Column(String(8))
    position = Column(Text)
    risk_level = Column(String(16), nullable=False, default="high")
    source = Column(String(128))
    added_at = Column(DateTime(timezone=True), default=_now)
