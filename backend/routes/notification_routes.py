"""
Notification API Routes
Provides REST endpoints for notification management and monitoring.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.alerts import NotificationService
from models.schemas.alerts import (
    NotificationQueueResponse,
    NotificationLogResponse,
    NotificationHistoryResponse,
    NotificationQueueStatusResponse,
    ProcessQueueResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.get("/status", response_model=NotificationQueueStatusResponse)
async def get_queue_status(
    db: Session = Depends(get_db),
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
