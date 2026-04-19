"""
Admin Router
GET /admin/stats     - Dashboard summary counts
GET /admin/pep/list  - View PEP list
POST /admin/pep      - Add PEP entry
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AMLCheck, AuditEvent, KYCSubmission, PEPEntry

router = APIRouter()


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """
    Dashboard summary: KYC counts by status, AML flag counts,
    recent audit events count, 24h activity.
    """
    # KYC counts by status
    kyc_result = await db.execute(
        select(
            KYCSubmission.status, func.count(KYCSubmission.id).label("count")
        ).group_by(KYCSubmission.status)
    )
    kyc_counts = {row.status: row.count for row in kyc_result}

    # AML counts
    aml_total = await db.execute(select(func.count(AMLCheck.id)))
    aml_flag = await db.execute(
        select(func.count(AMLCheck.id)).where(AMLCheck.flagged == True)
    )
    aml_pep = await db.execute(
        select(func.count(AMLCheck.id)).where(AMLCheck.pep_match == True)
    )

    # Audit events in last 24h
    since_24h = datetime.now(timezone.utc) - timedelta(hours=24)
    audit_24h = await db.execute(
        select(func.count(AuditEvent.id)).where(AuditEvent.created_at >= since_24h)
    )

    return {
        "kyc": {
            "total": sum(kyc_counts.values()),
            "by_status": kyc_counts,
            "pending": kyc_counts.get("pending", 0),
            "review": kyc_counts.get("review", 0),
            "verified": kyc_counts.get("verified", 0),
            "rejected": kyc_counts.get("rejected", 0),
        },
        "aml": {
            "total": aml_total.scalar_one(),
            "flagged": aml_flag.scalar_one(),
            "pep_matches": aml_pep.scalar_one(),
        },
        "audit": {
            "events_last_24h": audit_24h.scalar_one(),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/pep/list")
async def list_pep(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """View the current PEP (Politically Exposed Persons) list."""
    result = await db.execute(
        select(PEPEntry).order_by(PEPEntry.added_at.desc()).limit(limit)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "full_name": e.full_name,
            "aliases": e.aliases,
            "country": e.country,
            "position": e.position,
            "risk_level": e.risk_level,
            "source": e.source,
            "added_at": e.added_at,
        }
        for e in entries
    ]


class PEPCreateRequest(BaseModel):
    full_name: str
    aliases: List[str] = []
    country: Optional[str] = None
    position: Optional[str] = None
    risk_level: str = "high"
    source: Optional[str] = None


@router.post("/pep", status_code=201)
async def add_pep_entry(body: PEPCreateRequest, db: AsyncSession = Depends(get_db)):
    """Add an entry to the PEP list."""
    entry = PEPEntry(
        full_name=body.full_name,
        aliases=body.aliases,
        country=body.country,
        position=body.position,
        risk_level=body.risk_level,
        source=body.source,
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return {"id": entry.id, "full_name": entry.full_name, "status": "added"}


@router.delete("/pep/{pep_id}", status_code=204)
async def remove_pep_entry(pep_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(PEPEntry).where(PEPEntry.id == pep_id))
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(404, f"PEP entry #{pep_id} not found")
    await db.delete(entry)
    await db.commit()
