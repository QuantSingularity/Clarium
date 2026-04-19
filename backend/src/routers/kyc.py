"""
KYC Router
POST /kyc/submit       - Submit KYC application
POST /kyc/upload/{id}  - Upload identity document
GET  /kyc/status/{id}  - Get KYC status for user
PATCH /kyc/review/{id} - Admin review decision
GET  /kyc/queue        - Admin: list pending/review cases
"""

import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..database import get_db
from ..models import KYCSubmission
from ..schemas import KYCReviewRequest, KYCStatusResponse, KYCSubmitRequest
from ..services.audit_service import log_event
from ..services.kyc_service import (
    compute_identity_score,
    determine_kyc_status,
    is_valid_transition,
    run_ocr,
)
from ..services.webhook_service import queue_event

router = APIRouter()
logger = logging.getLogger("clarium.kyc")


@router.post("/submit", response_model=KYCStatusResponse, status_code=201)
async def submit_kyc(
    body: KYCSubmitRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a KYC application.
    Triggers document processing via OCR and identity scoring.
    """
    # Check for duplicate
    existing = await db.execute(
        select(KYCSubmission).where(KYCSubmission.user_id == body.user_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"KYC already submitted for user '{body.user_id}'")

    submission = KYCSubmission(
        user_id=body.user_id,
        full_name=body.full_name,
        date_of_birth=body.date_of_birth,
        nationality=body.nationality,
        document_type=body.document_type,
        document_number=body.document_number,
        status="pending",
    )
    db.add(submission)
    await db.flush()

    await log_event(
        db,
        entity_type="kyc",
        entity_id=body.user_id,
        event_type="kyc.submitted",
        payload=body.model_dump(mode="json"),
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    await db.refresh(submission)
    return submission


@router.post("/upload/{user_id}", status_code=200)
async def upload_document(
    user_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Upload an identity document for a pending KYC application.
    Triggers OCR processing and updates identity score.
    """
    result = await db.execute(
        select(KYCSubmission).where(KYCSubmission.user_id == user_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, f"KYC submission not found for user '{user_id}'")
    if submission.status not in ("pending", "review"):
        raise HTTPException(
            400, f"Cannot upload document in status '{submission.status}'"
        )

    # Validate file size
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    content = await file.read()
    if len(content) > max_bytes:
        raise HTTPException(413, f"File too large. Max {settings.max_upload_size_mb}MB")

    # Validate file type
    allowed_types = {"image/jpeg", "image/png", "application/pdf"}
    if file.content_type not in allowed_types:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")

    # Save file
    os.makedirs(settings.upload_dir, exist_ok=True)
    ext = os.path.splitext(file.filename or "doc")[1] or ".bin"
    filename = f"{user_id}_{uuid.uuid4().hex}{ext}"
    doc_path = os.path.join(settings.upload_dir, filename)

    with open(doc_path, "wb") as f:
        f.write(content)

    # Update status to processing
    submission.status = "processing"
    submission.document_uri = doc_path
    submission.updated_at = datetime.now(timezone.utc)

    await log_event(
        db,
        entity_type="kyc",
        entity_id=user_id,
        event_type="kyc.document_uploaded",
        payload={"filename": filename, "size_bytes": len(content)},
        ip_address=request.client.host if request.client else None,
    )

    # Run OCR
    ocr_result = await run_ocr(
        doc_path,
        submission.document_type,
        submission.full_name,
        submission.document_number,
    )
    submission.ocr_raw = ocr_result
    submission.ocr_confidence = ocr_result.get("confidence", 0.0)

    # Compute identity score
    identity_score, breakdown = compute_identity_score(
        ocr_result,
        submission.full_name,
        submission.document_number,
        submission.date_of_birth,
        submission.nationality,
    )
    submission.identity_score = identity_score

    # Determine new status
    new_status = determine_kyc_status(identity_score)
    submission.status = new_status
    submission.updated_at = datetime.now(timezone.utc)

    if new_status == "verified":
        submission.verified_at = datetime.now(timezone.utc)
    elif new_status == "rejected":
        submission.rejected_at = datetime.now(timezone.utc)

    # Log OCR + scoring
    await log_event(
        db,
        entity_type="kyc",
        entity_id=user_id,
        event_type=f"kyc.{new_status}",
        payload={
            "identity_score": identity_score,
            "ocr_confidence": submission.ocr_confidence,
            "score_breakdown": breakdown,
            "new_status": new_status,
        },
    )

    # Queue webhook
    await queue_event(
        db,
        f"kyc.{new_status}",
        {
            "user_id": user_id,
            "status": new_status,
            "identity_score": identity_score,
        },
    )

    await db.commit()
    return {
        "user_id": user_id,
        "status": new_status,
        "identity_score": identity_score,
        "ocr_confidence": submission.ocr_confidence,
        "message": f"Document processed. Status: {new_status}",
    }


@router.get("/status/{user_id}", response_model=KYCStatusResponse)
async def get_kyc_status(user_id: str, db: AsyncSession = Depends(get_db)):
    """Get the current KYC status for a user."""
    result = await db.execute(
        select(KYCSubmission).where(KYCSubmission.user_id == user_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, f"KYC submission not found for user '{user_id}'")
    return submission


@router.patch("/review/{user_id}", response_model=KYCStatusResponse)
async def review_kyc(
    user_id: str,
    body: KYCReviewRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Admin: manually set KYC status (verified/rejected) with notes."""
    result = await db.execute(
        select(KYCSubmission).where(KYCSubmission.user_id == user_id)
    )
    submission = result.scalar_one_or_none()
    if not submission:
        raise HTTPException(404, f"User '{user_id}' not found")

    if not is_valid_transition(submission.status, body.status):
        raise HTTPException(
            400,
            f"Invalid transition: {submission.status} → {body.status}",
        )

    old_status = submission.status
    submission.status = body.status
    submission.updated_at = datetime.now(timezone.utc)
    if body.reviewer_notes:
        submission.reviewer_notes = body.reviewer_notes
    if body.status == "verified":
        submission.verified_at = datetime.now(timezone.utc)
    elif body.status == "rejected":
        submission.rejected_at = datetime.now(timezone.utc)

    await log_event(
        db,
        entity_type="kyc",
        entity_id=user_id,
        event_type=f"kyc.{body.status}",
        payload={
            "old_status": old_status,
            "new_status": body.status,
            "reviewer_notes": body.reviewer_notes,
        },
        actor_id="admin",
        ip_address=request.client.host if request.client else None,
    )

    await queue_event(
        db,
        f"kyc.{body.status}",
        {
            "user_id": user_id,
            "status": body.status,
            "notes": body.reviewer_notes,
        },
    )

    await db.commit()
    await db.refresh(submission)
    return submission


@router.get("/queue")
async def kyc_queue(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """Admin: list KYC submissions, optionally filtered by status."""
    q = select(KYCSubmission).order_by(KYCSubmission.submitted_at.desc())
    if status:
        q = q.where(KYCSubmission.status == status)
    q = q.limit(limit).offset(offset)

    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        {
            "user_id": r.user_id,
            "status": r.status,
            "full_name": r.full_name,
            "identity_score": r.identity_score,
            "submitted_at": r.submitted_at,
            "updated_at": r.updated_at,
        }
        for r in rows
    ]
