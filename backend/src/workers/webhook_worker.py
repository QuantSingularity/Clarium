"""
Clarium Webhook Worker
======================
Background process that polls for pending/retrying webhook deliveries
and dispatches them with exponential backoff.
"""

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import and_, select

from ..database import AsyncSessionLocal
from ..models import WebhookDelivery, WebhookRegistration
from ..services.webhook_service import deliver_webhook

logger = logging.getLogger("clarium.webhook-worker")

POLL_INTERVAL_SECONDS = 10


async def process_pending():
    """Process all pending and due-for-retry webhook deliveries."""
    async with AsyncSessionLocal() as db:
        now = datetime.now(timezone.utc)

        result = await db.execute(
            select(WebhookDelivery)
            .where(
                and_(
                    WebhookDelivery.status.in_(["pending", "retrying"]),
                    (WebhookDelivery.next_retry_at == None)
                    | (WebhookDelivery.next_retry_at <= now),
                )
            )
            .limit(50)
        )
        deliveries = result.scalars().all()

        if not deliveries:
            return

        logger.info(f"Processing {len(deliveries)} webhook deliveries...")

        for delivery in deliveries:
            # Fetch the associated webhook registration
            wh_result = await db.execute(
                select(WebhookRegistration).where(
                    WebhookRegistration.id == delivery.webhook_id
                )
            )
            webhook = wh_result.scalar_one_or_none()
            if not webhook or not webhook.is_active:
                delivery.status = "failed"
                continue

            await deliver_webhook(db, delivery, webhook)

        await db.commit()


async def run():
    logger.info("Clarium webhook worker started")
    while True:
        try:
            await process_pending()
        except Exception as e:
            logger.error(f"Webhook worker error: {e}", exc_info=True)
        await asyncio.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level="INFO")
    asyncio.run(run())
