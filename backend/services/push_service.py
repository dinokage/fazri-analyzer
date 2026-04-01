"""
PushService — sends Web Push notifications to subscribed browser sessions.

Uses pywebpush (VAPID) to deliver push messages. Gracefully no-ops when
VAPID keys are not configured or pywebpush is not installed.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from config import settings
from models.db.push_subscriptions import PushSubscription

logger = logging.getLogger(__name__)


def _build_payload(title: str, body: str, url: str = "/dashboard/alerts") -> str:
    return json.dumps({"title": title, "body": body, "url": url})


def send_push_to_all(db: Session, title: str, body: str, url: str = "/dashboard/alerts") -> int:
    """
    Send a Web Push notification to every stored subscription.
    Returns the number of successful deliveries.
    Non-fatal: logs errors and removes stale (410 Gone) subscriptions.
    """
    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.debug("Web Push skipped: VAPID keys not configured")
        return 0

    try:
        from pywebpush import webpush, WebPushException  # type: ignore
    except ImportError:
        logger.warning("pywebpush is not installed — Web Push notifications disabled")
        return 0

    subscriptions: List[PushSubscription] = db.query(PushSubscription).all()
    payload = _build_payload(title, body, url)
    sent = 0
    stale_ids = []

    for sub in subscriptions:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={
                    "sub": f"mailto:{settings.VAPID_CLAIMS_EMAIL}",
                },
            )
            sent += 1
        except WebPushException as exc:
            if exc.response and exc.response.status_code == 410:
                # Subscription expired — remove it
                stale_ids.append(sub.id)
                logger.info("Removed expired push subscription endpoint=%s", sub.endpoint[:40])
            else:
                logger.warning("Push delivery failed for endpoint=%s: %s", sub.endpoint[:40], exc)
        except Exception as exc:
            logger.warning("Unexpected push error for endpoint=%s: %s", sub.endpoint[:40], exc)

    # Clean up stale subscriptions
    if stale_ids:
        db.query(PushSubscription).filter(PushSubscription.id.in_(stale_ids)).delete(synchronize_session=False)
        db.commit()

    logger.info("Web Push: sent=%d stale_removed=%d total_subs=%d", sent, len(stale_ids), len(subscriptions))
    return sent
