"""
Background Aruba WiFi device association poller.

Polls the ArubaAOS8Client at a configurable interval, diffs current vs
previous client list to detect zone movements, and feeds SensorEvents into
the EventIngestionService.

Startup (called from main.py lifespan):
    task = asyncio.create_task(run_aruba_poller())
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List

from config import settings
from connectors.aruba_client import get_aruba_client
from database.connection import SessionLocal
from models.schemas.sensor_events import SensorEvent
from services.event_ingestion_service import get_event_ingestion_service

logger = logging.getLogger(__name__)


async def run_aruba_poller() -> None:
    """
    Async loop that polls the Aruba AOS8 controller forever.

    - Polls every ARUBA_POLL_INTERVAL_SECONDS
    - Diffs current vs previous client list to detect movements
    - Logs aggregate stats every 60 seconds
    - Handles connection failures gracefully
    """
    client = get_aruba_client()
    interval = settings.ARUBA_POLL_INTERVAL_SECONDS

    previous_events: List[SensorEvent] = []
    stats = {"polled": 0, "resolved": 0, "poll_cycles": 0}
    last_stats_log = datetime.now(timezone.utc)

    logger.info(
        "Aruba poller started — url=%s interval=%ds",
        settings.ARUBA_BASE_URL,
        interval,
    )

    # Redis client for health status reporting
    _redis = None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.Redis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, socket_timeout=1
        )
    except Exception as e:
        _redis = None
        logger.debug(
            "Redis init failed for aruba_poller (host=%s, port=%s): %s",
            settings.REDIS_HOST, settings.REDIS_PORT, e, exc_info=True
        )

    while True:
        try:
            current_events = await client.get_associated_clients()

            if previous_events or current_events:
                # Diff to detect zone movements
                movement_events = await client.detect_movements(
                    previous=previous_events,
                    current=current_events,
                )

                if movement_events:
                    with SessionLocal() as db:
                        svc = get_event_ingestion_service(db)
                        results = await svc.ingest_batch(
                            movement_events,
                            organization_id=settings.ARUBA_ORGANIZATION_ID,
                        )

                    resolved_count = sum(1 for r in results if r is not None)
                    stats["polled"] += len(movement_events)
                    stats["resolved"] += resolved_count

            previous_events = current_events
            stats["poll_cycles"] += 1

            # Publish poller status to Redis for health endpoint
            now = datetime.now(timezone.utc)
            if _redis:
                try:
                    await _redis.set("aruba:last_poll", now.isoformat(), ex=300)
                    await _redis.set("aruba:clients_online", len(current_events), ex=300)
                except Exception as e:
                    logger.debug("Redis status write failed in aruba_poller: %s", e)

            # Log aggregate stats every 60 seconds
            if (now - last_stats_log).total_seconds() >= 60:
                logger.info(
                    "Aruba poller stats — movement_events=%d resolved=%d cycles=%d clients_online=%d",
                    stats["polled"],
                    stats["resolved"],
                    stats["poll_cycles"],
                    len(current_events),
                )
                last_stats_log = now

        except asyncio.CancelledError:
            logger.info("Aruba poller cancelled — shutting down")
            if _redis:
                await _redis.aclose()
            break
        except Exception as exc:
            logger.warning(
                "Aruba poll failed: %s — will retry in %ds",
                exc,
                interval,
            )

        await asyncio.sleep(interval)
