"""Audit Trail Router"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import AuditEvent
from ..schemas import AuditEventResponse
from ..services.audit_service import verify_chain

router = APIRouter()


@router.get("/trail/{entity_id}", response_model=list[AuditEventResponse])
async def get_audit_trail(
    entity_id: str,
    entity_type: str | None = Query(None),
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Get the immutable audit trail for an entity (user, transaction, etc.)."""
    q = (
        select(AuditEvent)
        .where(AuditEvent.entity_id == entity_id)
        .order_by(AuditEvent.created_at.asc())
        .limit(limit)
    )

    if entity_type:
        q = q.where(AuditEvent.entity_type == entity_type)

    result = await db.execute(q)
    return result.scalars().all()


@router.get("/verify")
async def verify_audit_chain(db: AsyncSession = Depends(get_db)):
    """Verify integrity of the entire audit chain (tamper detection)."""
    return await verify_chain(db)


@router.get("/recent")
async def recent_events(
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AuditEvent)
        .order_by(AuditEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()
