"""
AML Router
POST /aml/check          - Run AML check on a transaction
GET  /aml/flags          - List flagged transactions
GET  /aml/flags/{id}     - Get AML check detail
PATCH /aml/review/{id}   - Admin: update review status
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AMLCheck
from ..schemas import AMLCheckRequest, AMLCheckResponse
from ..services.aml_service import run_aml_check
from ..services.audit_service import log_event
from ..services.webhook_service import queue_event

router = APIRouter()
logger = logging.getLogger("clarium.aml")


@router.post("/check", response_model=AMLCheckResponse, status_code=201)
async def aml_check(
    body: AMLCheckRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Run AML checks on a transaction.
    Checks: amount threshold, velocity, geographic risk, PEP matching.
    """
    risk_score, flagged, flag_reasons, pep_match, pep_details = await run_aml_check(
        db,
        transaction_id=body.transaction_id,
        user_id=body.user_id,
        amount=body.amount,
        currency=body.currency,
        source_country=body.source_country,
        destination_country=body.destination_country,
    )

    check = AMLCheck(
        transaction_id=body.transaction_id,
        user_id=body.user_id,
        amount=body.amount,
        currency=body.currency,
        source_country=body.source_country,
        destination_country=body.destination_country,
        risk_score=risk_score,
        flagged=flagged,
        flag_reasons=flag_reasons,
        pep_match=pep_match,
        pep_match_details=pep_details,
        status="flagged" if flagged else "clear",
    )
    db.add(check)
    await db.flush()

    await log_event(
        db,
        entity_type="aml",
        entity_id=body.transaction_id,
        event_type="aml.flagged" if flagged else "aml.clear",
        payload={
            "amount": float(body.amount),
            "currency": body.currency,
            "risk_score": risk_score,
            "flag_reasons": flag_reasons,
            "pep_match": pep_match,
        },
        ip_address=request.client.host if request.client else None,
    )

    if flagged:
        await queue_event(
            db,
            "aml.flagged",
            {
                "transaction_id": body.transaction_id,
                "user_id": body.user_id,
                "risk_score": risk_score,
                "flag_reasons": flag_reasons,
            },
        )

    await db.commit()
    await db.refresh(check)
    return check


@router.get("/flags")
async def list_flags(
    flagged_only: bool = Query(True),
    user_id: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    """List AML checks, optionally filtered to flagged only."""
    q = select(AMLCheck).order_by(AMLCheck.checked_at.desc())
    if flagged_only:
        q = q.where(AMLCheck.flagged == True)
    if user_id:
        q = q.where(AMLCheck.user_id == user_id)
    q = q.limit(limit).offset(offset)

    result = await db.execute(q)
    rows = result.scalars().all()
    return [
        {
            "id": r.id,
            "transaction_id": r.transaction_id,
            "user_id": r.user_id,
            "amount": float(r.amount),
            "currency": r.currency,
            "risk_score": r.risk_score,
            "flagged": r.flagged,
            "flag_reasons": r.flag_reasons,
            "pep_match": r.pep_match,
            "status": r.status,
            "checked_at": r.checked_at,
        }
        for r in rows
    ]


@router.get("/flags/{check_id}")
async def get_flag(check_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AMLCheck).where(AMLCheck.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(404, f"AML check #{check_id} not found")
    return check


@router.patch("/review/{check_id}")
async def review_flag(
    check_id: int,
    status: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Admin: update AML case status (under_review → escalated | cleared)."""
    valid = {"under_review", "escalated", "cleared"}
    if status not in valid:
        raise HTTPException(400, f"Status must be one of: {valid}")

    result = await db.execute(select(AMLCheck).where(AMLCheck.id == check_id))
    check = result.scalar_one_or_none()
    if not check:
        raise HTTPException(404, f"AML check #{check_id} not found")

    old_status = check.status
    check.status = status

    await log_event(
        db,
        entity_type="aml",
        entity_id=check.transaction_id,
        event_type=f"aml.{status}",
        payload={"old_status": old_status, "new_status": status},
        actor_id="admin",
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return {"transaction_id": check.transaction_id, "status": status}
