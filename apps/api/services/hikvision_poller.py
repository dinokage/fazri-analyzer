"""
Background Hikvision RFID event poller.

Polls the HikvisionISAPIClient at a configurable interval and feeds all
fetched SensorEvents into the EventIngestionService.

Startup (called from main.py lifespan):
    task = asyncio.create_task(run_hikvision_poller())

Shutdown:
    task.cancel()
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta

from config import settings
from connectors.hikvision_client import get_hikvision_client
from database.connection import SessionLocal
from services.event_ingestion_service import get_event_ingestion_service

logger = logging.getLogger(__name__)


async def run_hikvision_poller() -> None:
    """
    Async loop that polls the Hikvision ISAPI endpoint forever.

    - Polls every HIKVISION_POLL_INTERVAL_SECONDS
    - Tracks last-seen event timestamp to avoid reprocessing
    - Logs aggregate stats every 60 seconds
    - Handles connection failures gracefully (logs warning, skips until next interval)
    """
    client = get_hikvision_client()
    interval = settings.HIKVISION_POLL_INTERVAL_SECONDS

    # Bootstrap: go back 5 minutes on first poll
    last_seen_ts = datetime.now(timezone.utc) - timedelta(minutes=5)

    stats = {"polled": 0, "resolved": 0, "poll_cycles": 0}
    last_stats_log = datetime.now(timezone.utc)

    logger.info(
        "Hikvision poller started — url=%s interval=%ds",
        settings.HIKVISION_BASE_URL,
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
        logger.debug("Redis init failed for hikvision_poller: %s", e, exc_info=True)

    while True:
        try:
            events = await client.poll_access_events(since=last_seen_ts)

            if events:
                # Update watermark before ingesting to avoid re-fetch on partial failure
                newest_ts = max(e.timestamp for e in events)
                if newest_ts > last_seen_ts:
                    last_seen_ts = newest_ts

                db = SessionLocal()
                try:
                    svc = get_event_ingestion_service(db)
                    results = await svc.ingest_batch(
                        events,
                        organization_id=settings.HIKVISION_ORGANIZATION_ID,
                    )
                finally:
                    db.close()

                resolved_count = sum(1 for r in results if r is not None)
                stats["polled"] += len(events)
                stats["resolved"] += resolved_count

            stats["poll_cycles"] += 1

            # Publish poller status to Redis for health endpoint
            now = datetime.now(timezone.utc)
            if _redis:
                try:
                    await _redis.set("hikvision:last_poll", now.isoformat(), ex=300)
                    await _redis.set("hikvision:events_today", stats["polled"], ex=86400)
                except Exception as e:
                    logger.debug("Redis status write failed in hikvision_poller: %s", e)

            # Log aggregate stats every 60 seconds
            if (now - last_stats_log).total_seconds() >= 60:
                logger.info(
                    "Hikvision poller stats — polled=%d resolved=%d cycles=%d",
                    stats["polled"],
                    stats["resolved"],
                    stats["poll_cycles"],
                )
                last_stats_log = now

        except asyncio.CancelledError:
            logger.info("Hikvision poller cancelled — shutting down")
            if _redis:
                await _redis.aclose()
            break
        except Exception as exc:
            logger.warning(
                "Hikvision poll failed: %s — will retry in %ds",
                exc,
                interval,
            )

        await asyncio.sleep(interval)
