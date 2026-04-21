"""
Notification API Routes
Provides REST endpoints for notification management and monitoring.
"""

import logging
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from services.alerts import NotificationService
from models.db.push_subscriptions import PushSubscription
from models.schemas.alerts import (
    NotificationQueueResponse,
    NotificationLogResponse,
    NotificationHistoryResponse,
    NotificationQueueStatusResponse,
    ProcessQueueResponse,
)
from auth.dependencies import require_staff, require_org_member
from auth.models import AuthenticatedUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/status", response_model=NotificationQueueStatusResponse)
async def get_queue_status(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member)
):
    """
    Get the current status of the notification queue.

    Returns counts of pending, failed, and sent notifications,
    plus the list of enabled notification providers.
    """
    service = NotificationService(db)
    status = service.get_queue_status()
    return NotificationQueueStatusResponse(**status)


@router.post("/process", response_model=ProcessQueueResponse)
async def process_notification_queue(
    batch_size: int = Query(50, ge=1, le=200, description="Number of notifications to process"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member)
):
    """
    Process pending notifications in the queue.

    This endpoint is typically called by a background scheduler.
    In production, consider using a dedicated worker process.

    Args:
        batch_size: Maximum number of notifications to process in this call
    """
    service = NotificationService(db)
    results = service.process_queue(batch_size=batch_size)

    return ProcessQueueResponse(
        message="Notification queue processed",
        results=results,
    )


@router.get("/history", response_model=NotificationHistoryResponse)
async def get_notification_history(
    staff_id: Optional[UUID] = Query(None, description="Filter by staff member"),
    alert_id: Optional[UUID] = Query(None, description="Filter by alert"),
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member)
):
    """
    Get notification delivery history.

    Can be filtered by staff member and/or alert ID.
    """
    service = NotificationService(db)
    logs = service.get_notification_history(
        staff_id=staff_id,
        alert_id=alert_id,
        limit=limit,
    )

    return NotificationHistoryResponse(
        total=len(logs),
        logs=[_log_to_response(log) for log in logs],
    )


@router.get("/staff/{staff_id}/history", response_model=NotificationHistoryResponse)
async def get_staff_notification_history(
    staff_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member)
):
    """
    Get notification history for a specific staff member.
    """
    service = NotificationService(db)
    logs = service.get_notification_history(
        staff_id=staff_id,
        limit=limit,
    )

    return NotificationHistoryResponse(
        total=len(logs),
        logs=[_log_to_response(log) for log in logs],
    )


@router.get("/alert/{alert_id}/history", response_model=NotificationHistoryResponse)
async def get_alert_notification_history(
    alert_id: UUID,
    limit: int = Query(50, ge=1, le=200, description="Maximum results to return"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member)
):
    """
    Get notification history for a specific alert.
    """
    service = NotificationService(db)
    logs = service.get_notification_history(
        alert_id=alert_id,
        limit=limit,
    )

    return NotificationHistoryResponse(
        total=len(logs),
        logs=[_log_to_response(log) for log in logs],
    )


def _log_to_response(log) -> NotificationLogResponse:
    """Convert NotificationLog to response schema"""
    # Get the notification to get subject if available
    subject = ""
    alert_id = None
    if log.notification:
        subject = log.notification.title
        alert_id = log.notification.alert_id

    return NotificationLogResponse(
        id=log.id,
        notification_id=log.notification_id,
        staff_id=log.recipient_id,
        alert_id=alert_id,
        channel=log.channel.value if hasattr(log.channel, 'value') else log.channel,
        recipient=log.recipient_address or "",
        subject=subject,
        status=log.status.value if hasattr(log.status, 'value') else log.status,
        sent_at=log.sent_at,
        created_at=log.sent_at,  # Use sent_at as created_at since no separate created_at field
    )


# ============================================================================
# Web Push (VAPID)
# ============================================================================

class PushSubscriptionBody(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.get("/vapid-public-key", summary="Get VAPID public key for browser push subscription")
async def get_vapid_public_key(
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict[str, Any]:
    """Return the VAPID public key so the client can create a PushSubscription."""
    if not settings.VAPID_PUBLIC_KEY:
        raise HTTPException(status_code=503, detail="Push notifications are not configured on this server")
    return {"publicKey": settings.VAPID_PUBLIC_KEY}


@router.post("/push-subscription", summary="Register or refresh a browser push subscription")
async def save_push_subscription(
    body: PushSubscriptionBody,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict[str, str]:
    """
    Upsert a Web Push subscription for the current user.
    The browser calls this after Notification.requestPermission() is granted.
    """
    user_id = current_user.email or str(current_user.entity_id or "")
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == body.endpoint).first()
    if existing:
        existing.p256dh = body.p256dh
        existing.auth = body.auth
        existing.user_id = user_id
    else:
        sub = PushSubscription(
            user_id=user_id,
            endpoint=body.endpoint,
            p256dh=body.p256dh,
            auth=body.auth,
        )
        db.add(sub)
    db.commit()
    return {"status": "subscribed"}


@router.delete("/push-subscription", summary="Unregister a browser push subscription")
async def delete_push_subscription(
    body: PushSubscriptionBody,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_member),
) -> Dict[str, str]:
    """Remove a push subscription (called when the user disables notifications)."""
    db.query(PushSubscription).filter(PushSubscription.endpoint == body.endpoint).delete()
    db.commit()
    return {"status": "unsubscribed"}
