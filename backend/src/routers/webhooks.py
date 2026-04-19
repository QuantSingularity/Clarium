"""Webhooks Router"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db
from ..models import WebhookDelivery, WebhookRegistration
from ..schemas import WebhookCreateRequest, WebhookDeliveryResponse, WebhookResponse

router = APIRouter()


@router.post("/", response_model=WebhookResponse, status_code=201)
async def register_webhook(
    body: WebhookCreateRequest, db: AsyncSession = Depends(get_db)
):
    wh = WebhookRegistration(url=body.url, secret=body.secret, events=body.events)
    db.add(wh)
    await db.commit()
    await db.refresh(wh)
    return wh


@router.get("/", response_model=list[WebhookResponse])
async def list_webhooks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WebhookRegistration).order_by(WebhookRegistration.created_at.desc())
    )
    return result.scalars().all()


@router.delete("/{webhook_id}", status_code=204)
async def delete_webhook(webhook_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WebhookRegistration).where(WebhookRegistration.id == webhook_id)
    )
    wh = result.scalar_one_or_none()
    if not wh:
        raise HTTPException(404, "Webhook not found")
    await db.delete(wh)
    await db.commit()


@router.get("/{webhook_id}/deliveries", response_model=list[WebhookDeliveryResponse])
async def list_deliveries(webhook_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(WebhookDelivery)
        .where(WebhookDelivery.webhook_id == webhook_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(100)
    )
    return result.scalars().all()
