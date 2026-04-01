"""
Outgoing webhook management routes.
Admins can register HTTP endpoints that receive real-time event notifications.
"""

import ipaddress
import logging
import re
import socket
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, field_validator
from sqlalchemy.orm import Session

from auth.dependencies import require_admin
from auth.models import AuthenticatedUser
from database.connection import get_db
from services.webhook_service import WEBHOOK_EVENTS, WebhookService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/webhooks", tags=["Webhooks"])


def _validate_webhook_url(url: str) -> str:
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("URL must use http or https")
    host = parsed.hostname or ""
    if not host:
        raise ValueError("URL must include a hostname")

    # Resolve hostname and reject any private/non-public addresses
    try:
        addrinfos = socket.getaddrinfo(host, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        raise ValueError(f"Cannot resolve hostname: {host}")

    for family, _, _, _, sockaddr in addrinfos:
        ip = ipaddress.ip_address(sockaddr[0])
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_unspecified
            or ip.is_multicast
            or ip.is_reserved
        ):
            raise ValueError("URL resolves to a private/internal address")

    return url


# ---- Schemas ----

class WebhookCreate(BaseModel):
    url: str
    events: List[str]

    @field_validator("url")
    @classmethod
    def url_must_be_valid(cls, v: str) -> str:
        return _validate_webhook_url(v)

    @field_validator("events")
    @classmethod
    def events_not_empty(cls, v: List[str]) -> List[str]:
        if not v:
            raise ValueError("At least one event is required")
        for e in v:
            if e not in WEBHOOK_EVENTS:
                raise ValueError(f"Unknown event: {e}. Valid events: {WEBHOOK_EVENTS}")
        return v


class WebhookUpdate(BaseModel):
    url: Optional[str] = None
    events: Optional[List[str]] = None
    active: Optional[bool] = None

    @field_validator("url")
    @classmethod
    def url_must_be_valid(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return _validate_webhook_url(v)
        return v

    @field_validator("events")
    @classmethod
    def events_valid(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        if v is not None:
            if not v:
                raise ValueError("At least one event is required")
            for e in v:
                if e not in WEBHOOK_EVENTS:
                    raise ValueError(f"Unknown event: {e}")
        return v


class WebhookResponse(BaseModel):
    id: str
    url: str
    events: List[str]
    secret: str
    active: bool
    created_at: str

    model_config = {"from_attributes": True}


# ---- Endpoints ----

@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    """List all configured outgoing webhooks."""
    webhooks = WebhookService.list_webhooks(db)
    return [
        WebhookResponse(
            id=str(w.id),
            url=w.url,
            events=w.events_list,
            secret=w.secret,
            active=w.active,
            created_at=w.created_at.isoformat(),
        )
        for w in webhooks
    ]


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookCreate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    """Create a new outgoing webhook endpoint."""
    webhook = WebhookService.create_webhook(db, url=body.url, events=body.events)
    return WebhookResponse(
        id=str(webhook.id),
        url=webhook.url,
        events=webhook.events_list,
        secret=webhook.secret,
        active=webhook.active,
        created_at=webhook.created_at.isoformat(),
    )


@router.put("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: str,
    body: WebhookUpdate,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    """Update URL, events, or active status of a webhook."""
    webhook = WebhookService.update_webhook(
        db,
        webhook_id=webhook_id,
        url=body.url,
        events=body.events,
        active=body.active,
    )
    if not webhook:
        raise HTTPException(status_code=404, detail="Webhook not found")
    return WebhookResponse(
        id=str(webhook.id),
        url=webhook.url,
        events=webhook.events_list,
        secret=webhook.secret,
        active=webhook.active,
        created_at=webhook.created_at.isoformat(),
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
):
    """Delete a webhook endpoint."""
    deleted = WebhookService.delete_webhook(db, webhook_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Webhook not found")


@router.post("/{webhook_id}/test")
async def test_webhook(
    webhook_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
) -> Dict[str, Any]:
    """Send a test event to verify the webhook endpoint is reachable."""
    result = await WebhookService.send_test(db, webhook_id)
    return result
