"""
Clarium Audit Trail Service
===========================
Immutable, append-only compliance event log with SHA-256 hash chaining
for tamper evidence. Each row hashes its own content plus the hash of
the previous row, creating a verifiable chain.
"""

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import AuditEvent

logger = logging.getLogger("clarium.audit")


def _compute_hash(
    entity_type: str,
    entity_id: str,
    event_type: str,
    actor_id: Optional[str],
    payload: Dict[str, Any],
    created_at: datetime,
    prev_hash: Optional[str],
) -> str:
    """
    Compute SHA-256 hash of the event content + previous hash.
    This creates a tamper-evident chain: changing any past record
    breaks the hash of every subsequent record.
    """
    content = json.dumps(
        {
            "entity_type": entity_type,
            "entity_id": entity_id,
            "event_type": event_type,
            "actor_id": actor_id,
            "payload": payload,
            "created_at": created_at.isoformat(),
            "prev_hash": prev_hash or "",
        },
        sort_keys=True,
    )
    return hashlib.sha256(content.encode()).hexdigest()


async def log_event(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    event_type: str,
    payload: Dict[str, Any],
    actor_id: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> AuditEvent:
    """
    Append an immutable audit event.

    Parameters
    ----------
    entity_type : str   - "kyc" | "aml" | "webhook" | "admin"
    entity_id   : str   - ID of the entity being audited
    event_type  : str   - e.g. "kyc.submitted", "aml.flagged", "kyc.verified"
    payload     : dict  - Event-specific data (serializable)
    actor_id    : str   - Who triggered the event (user ID or service name)
    ip_address  : str   - Request IP for admin actions
    """
    # Get the latest hash to chain from
    last = await db.execute(
        select(AuditEvent.this_hash).order_by(AuditEvent.id.desc()).limit(1)
    )
    prev_hash = last.scalar_one_or_none()

    created_at = datetime.now(timezone.utc)

    this_hash = _compute_hash(
        entity_type, entity_id, event_type, actor_id, payload, created_at, prev_hash
    )

    event = AuditEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        event_type=event_type,
        actor_id=actor_id,
        payload=payload,
        ip_address=ip_address,
        prev_hash=prev_hash,
        this_hash=this_hash,
        created_at=created_at,
    )
    db.add(event)
    await db.flush()  # get ID without committing

    logger.info(
        f"Audit: [{event_type}] entity={entity_type}:{entity_id} "
        f"actor={actor_id} hash={this_hash[:16]}…"
    )
    return event


async def verify_chain(db: AsyncSession) -> Dict[str, Any]:
    """
    Verify the integrity of the entire audit chain.
    Returns a report indicating whether any records have been tampered with.
    """
    result = await db.execute(select(AuditEvent).order_by(AuditEvent.id.asc()))
    events = result.scalars().all()

    if not events:
        return {"valid": True, "checked": 0, "violations": []}

    violations = []
    for event in events:
        expected = _compute_hash(
            event.entity_type,
            event.entity_id,
            event.event_type,
            event.actor_id,
            event.payload,
            event.created_at,
            event.prev_hash,
        )
        if expected != event.this_hash:
            violations.append(
                {
                    "id": event.id,
                    "expected": expected,
                    "actual": event.this_hash,
                }
            )

    return {
        "valid": len(violations) == 0,
        "checked": len(events),
        "violations": violations,
    }
