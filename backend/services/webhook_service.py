"""
Outgoing webhook service for dispatching events to configured endpoints.
Supports Discord, Slack, and generic HTTP endpoints with HMAC-SHA256 signing.
"""

import asyncio
import hashlib
import hmac
import logging
import re
import secrets
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.db.webhooks import OutgoingWebhook

logger = logging.getLogger(__name__)

DISCORD_WEBHOOK_PATTERN = re.compile(
    r"^https://(discord\.com|discordapp\.com)/api/webhooks/"
)
SLACK_WEBHOOK_PATTERN = re.compile(r"^https://hooks\.slack\.com/services/")

WEBHOOK_EVENTS = [
    "ALERT_CREATED",
    "ALERT_ASSIGNED",
    "ALERT_ACKNOWLEDGED",
    "ALERT_RESOLVED",
    "ALERT_ESCALATED",
]

_event_config: Dict[str, Dict[str, str]] = {
    "ALERT_CREATED":      {"color": "#ef4444", "label": "Alert Created",      "emoji": "🚨"},
    "ALERT_ASSIGNED":     {"color": "#f97316", "label": "Alert Assigned",     "emoji": "👤"},
    "ALERT_ACKNOWLEDGED": {"color": "#3b82f6", "label": "Alert Acknowledged", "emoji": "✅"},
    "ALERT_RESOLVED":     {"color": "#22c55e", "label": "Alert Resolved",     "emoji": "🔒"},
    "ALERT_ESCALATED":    {"color": "#a855f7", "label": "Alert Escalated",    "emoji": "⬆️"},
}


def _is_discord(url: str) -> bool:
    return bool(DISCORD_WEBHOOK_PATTERN.match(url))


def _is_slack(url: str) -> bool:
    return bool(SLACK_WEBHOOK_PATTERN.match(url))


def _is_third_party(url: str) -> bool:
    return _is_discord(url) or _is_slack(url)


def _discord_payload(event: str, data: Dict[str, Any]) -> str:
    import json

    cfg = _event_config.get(event, {"color": "#6b7280", "label": event, "emoji": "•"})
    fields = []
    for key in ("title", "severity", "zone_id", "entity_id", "alert_id"):
        if key in data:
            fields.append({"name": key.replace("_", " ").title(), "value": str(data[key]), "inline": True})

    return json.dumps({
        "embeds": [{
            "title": f"{cfg['emoji']} {cfg['label']}",
            "color": int(cfg["color"].lstrip("#"), 16),
            "fields": fields,
            "timestamp": data.get("timestamp", ""),
            "footer": {"text": "Fazri Analyzer Webhooks"},
        }]
    })


def _slack_payload(event: str, data: Dict[str, Any]) -> str:
    import json

    cfg = _event_config.get(event, {"color": "#6b7280", "label": event, "emoji": "•"})
    fields = []
    for key in ("title", "severity", "zone_id", "entity_id", "alert_id"):
        if key in data:
            fields.append({"type": "mrkdwn", "text": f"*{key.replace('_', ' ').title()}:* {data[key]}"})

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": f"{cfg['emoji']} {cfg['label']}", "emoji": True}},
    ]
    if fields:
        blocks.append({"type": "section", "fields": fields})
    blocks.append({
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": f"Fazri Analyzer Webhooks • {data.get('timestamp', '')}"}],
    })

    return json.dumps({"attachments": [{"color": cfg["color"], "blocks": blocks}]})


class WebhookService:
    @staticmethod
    def _get_all_active(db: Session) -> List[OutgoingWebhook]:
        return db.query(OutgoingWebhook).filter(OutgoingWebhook.active == True).all()

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    @staticmethod
    def list_webhooks(db: Session) -> List[OutgoingWebhook]:
        return (
            db.query(OutgoingWebhook)
            .order_by(OutgoingWebhook.created_at.desc())
            .all()
        )

    @staticmethod
    def create_webhook(db: Session, url: str, events: List[str]) -> OutgoingWebhook:
        secret = f"whsec_{secrets.token_hex(24)}"
        webhook = OutgoingWebhook(
            url=url,
            events=",".join(events),
            secret=secret,
        )
        db.add(webhook)
        db.commit()
        db.refresh(webhook)
        return webhook

    @staticmethod
    def update_webhook(
        db: Session,
        webhook_id: str,
        url: Optional[str] = None,
        events: Optional[List[str]] = None,
        active: Optional[bool] = None,
    ) -> Optional[OutgoingWebhook]:
        webhook = db.query(OutgoingWebhook).filter(OutgoingWebhook.id == webhook_id).first()
        if not webhook:
            return None
        if url is not None:
            webhook.url = url
        if events is not None:
            webhook.events = ",".join(events)
        if active is not None:
            webhook.active = active
        from datetime import datetime
        webhook.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(webhook)
        return webhook

    @staticmethod
    def delete_webhook(db: Session, webhook_id: str) -> bool:
        webhook = db.query(OutgoingWebhook).filter(OutgoingWebhook.id == webhook_id).first()
        if not webhook:
            return False
        db.delete(webhook)
        db.commit()
        return True

    # ------------------------------------------------------------------
    # Delivery
    # ------------------------------------------------------------------

    @staticmethod
    def _sign(secret: str, body: str) -> str:
        return hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()

    @staticmethod
    async def _send(webhook: OutgoingWebhook, event: str, data: Dict[str, Any]) -> None:
        import json

        if _is_discord(webhook.url):
            body = _discord_payload(event, data)
        elif _is_slack(webhook.url):
            body = _slack_payload(event, data)
        else:
            body = json.dumps({"event": event, "data": data, "timestamp": data.get("timestamp", "")})

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if not _is_third_party(webhook.url):
            sig = hmac.new(webhook.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = sig
            headers["X-Webhook-Event"] = event

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(webhook.url, content=body, headers=headers)
                if not resp.is_success:
                    logger.warning("[Webhook] %s returned %d for %s", webhook.url, resp.status_code, event)
        except Exception as exc:
            logger.error("[Webhook] Failed to deliver to %s: %s", webhook.url, exc)

    @staticmethod
    async def _dispatch_async(event: str, data: Dict[str, Any]) -> None:
        db = SessionLocal()
        try:
            webhooks = (
                db.query(OutgoingWebhook)
                .filter(OutgoingWebhook.active == True)
                .all()
            )
            targets = [w for w in webhooks if event in w.events_list]
            await asyncio.gather(*[WebhookService._send(w, event, data) for w in targets])
        except Exception as exc:
            logger.error("[Webhook] Error dispatching %s: %s", event, exc)
        finally:
            db.close()

    @staticmethod
    def dispatch_event(event: str, data: Dict[str, Any]) -> None:
        """Fire-and-forget webhook dispatch. Safe to call from sync context."""
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(WebhookService._dispatch_async(event, data))
        except RuntimeError:
            # No running loop — use asyncio.run (e.g. in tests)
            asyncio.run(WebhookService._dispatch_async(event, data))

    # ------------------------------------------------------------------
    # Test
    # ------------------------------------------------------------------

    @staticmethod
    async def send_test(db: Session, webhook_id: str) -> Dict[str, Any]:
        import json

        webhook = db.query(OutgoingWebhook).filter(OutgoingWebhook.id == webhook_id).first()
        if not webhook:
            return {"success": False, "error": "Webhook not found"}

        event = "ALERT_CREATED"
        data = {
            "alert_id": "test-alert-id-000",
            "title": "Test Alert",
            "severity": "medium",
            "zone_id": "TEST_ZONE",
            "timestamp": "",
        }

        if _is_discord(webhook.url):
            body = _discord_payload(event, data)
        elif _is_slack(webhook.url):
            body = _slack_payload(event, data)
        else:
            body = json.dumps({"event": event, "data": data, "timestamp": "", "test": True})

        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if not _is_third_party(webhook.url):
            sig = hmac.new(webhook.secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            headers["X-Webhook-Signature"] = sig
            headers["X-Webhook-Event"] = event

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(webhook.url, content=body, headers=headers)
                return {"success": resp.is_success, "status": resp.status_code}
        except Exception as exc:
            return {"success": False, "error": str(exc)}
