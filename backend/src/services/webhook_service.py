"""
Clarium Webhook Service
=======================
Registers webhooks, queues deliveries, and dispatches with HMAC signing.
"""

import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import WebhookDelivery, WebhookRegistration

logger = logging.getLogger("clarium.webhook")


def _sign_payload(secret: str, payload: Dict[str, Any]) -> str:
    """Generate HMAC-SHA256 signature for a webhook payload."""
    body = json.dumps(payload, sort_keys=True).encode()
    return hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


async def queue_event(
    db: AsyncSession,
    event_type: str,
    payload: Dict[str, Any],
) -> int:
    """
    Find all matching registered webhooks and queue delivery records.
    Returns number of deliveries queued.
    """
    result = await db.execute(
        select(WebhookRegistration).where(WebhookRegistration.is_active == True)
    )
    webhooks = result.scalars().all()

    queued = 0
    for webhook in webhooks:
        events = webhook.events or ["*"]
        if "*" in events or event_type in events:
            delivery = WebhookDelivery(
                webhook_id=webhook.id,
                event_type=event_type,
                payload={
                    "event": event_type,
                    "data": payload,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
                status="pending",
            )
            db.add(delivery)
            queued += 1

    await db.flush()
    logger.info(f"Queued {queued} webhook deliveries for event: {event_type}")
    return queued


async def deliver_webhook(
    db: AsyncSession,
    delivery: WebhookDelivery,
    webhook: WebhookRegistration,
) -> bool:
    """
    Attempt to deliver a single webhook. Returns True on success.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Clarium-Event": delivery.event_type,
        "User-Agent": "Clarium-Webhook/0.1",
    }

    if webhook.secret:
        sig = _sign_payload(webhook.secret, delivery.payload)
        headers["X-Clarium-Signature"] = f"sha256={sig}"

    try:
        async with httpx.AsyncClient(
            timeout=settings.webhook_timeout_seconds
        ) as client:
            resp = await client.post(
                webhook.url,
                json=delivery.payload,
                headers=headers,
            )

        delivery.response_code = resp.status_code
        delivery.response_body = resp.text[:500]
        delivery.attempts += 1

        if resp.is_success:
            delivery.status = "delivered"
            delivery.delivered_at = datetime.now(timezone.utc)
            logger.info(
                f"Webhook delivered: delivery={delivery.id} "
                f"url={webhook.url} status={resp.status_code}"
            )
            return True
        else:
            raise httpx.HTTPStatusError(
                f"Non-2xx: {resp.status_code}", request=None, response=resp
            )

    except Exception as e:
        delivery.attempts += 1
        logger.warning(
            f"Webhook delivery failed: delivery={delivery.id} "
            f"url={webhook.url} error={e}"
        )

        if delivery.attempts >= settings.webhook_max_retries:
            delivery.status = "failed"
        else:
            delivery.status = "retrying"
            delivery.next_retry_at = datetime.now(timezone.utc) + timedelta(
                seconds=settings.webhook_retry_backoff_seconds * delivery.attempts
            )

        return False
