"""
Shared Redis alert cooldown gate.

Prevents duplicate alerts for the same (anomaly_type, source_device, entity)
combination within the ALERT_COOLDOWN_SECONDS window.

Used by:
  - EventIngestionService._create_alert()   (general sensor pipeline)
  - deepface_routes.deepface_webhook()      (legacy direct path, if still needed)
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

_alert_redis: Any = None


def get_alert_redis() -> Optional[Any]:
    """Return (or lazily connect) the Redis client used for cooldown keys."""
    global _alert_redis
    if _alert_redis is None:
        try:
            from config import settings
            import redis as _redis_lib

            _alert_redis = _redis_lib.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _alert_redis.ping()
            logger.debug(
                "Alert cooldown Redis connected: %s:%s db=%s",
                settings.REDIS_HOST,
                settings.REDIS_PORT,
                settings.REDIS_DB,
            )
        except Exception as exc:
            logger.warning(
                "Alert cooldown Redis unavailable: %s — duplicates may occur", exc
            )
            _alert_redis = None
    return _alert_redis


def cooldown_key(anomaly_type: str, source_device: str, entity_key: str) -> str:
    return f"fazri:alert_cd:{anomaly_type}:{source_device}:{entity_key}"


def set_alert_cooldown(
    anomaly_type: str,
    source_device: str,
    entity_key: str,
) -> bool:
    """
    Atomic NX gate.

    Returns True if the key was newly created (proceed with alert).
    Returns False if it already existed (suppressed).
    Returns True when Redis is unavailable so alerts are never silently dropped.
    """
    from config import settings

    r = get_alert_redis()
    if not r:
        logger.warning("Cooldown gate skipped — Redis unavailable, allowing alert")
        return True
    key = cooldown_key(anomaly_type, source_device, entity_key)
    try:
        result = r.set(key, "1", ex=settings.ALERT_COOLDOWN_SECONDS, nx=True)
        created = result is not None
        logger.debug(
            "Cooldown NX set: key=%s ttl=%s created=%s",
            key,
            settings.ALERT_COOLDOWN_SECONDS,
            created,
        )
        return created
    except Exception as exc:
        logger.error("Cooldown set FAILED for key=%s: %s", key, exc)
        return True  # Allow on Redis error


def delete_alert_cooldown(
    anomaly_type: str,
    source_device: str,
    entity_key: str,
) -> None:
    """Delete the cooldown key so alert creation can be retried immediately."""
    r = get_alert_redis()
    if not r:
        return
    key = cooldown_key(anomaly_type, source_device, entity_key)
    try:
        r.delete(key)
        logger.debug("Cooldown key deleted for retry: key=%s", key)
    except Exception as exc:
        logger.error("Cooldown delete FAILED for key=%s: %s", key, exc)
