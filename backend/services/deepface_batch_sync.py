"""
DeepFace Batch Sync Service.

Runs as an asyncio background task that periodically reads new face-detection
records directly from the DeepFace pgvector PostgreSQL database and reconciles
them into the fazri-analyzer Neo4j graph.

This acts as a reliability safety-net: if a webhook call is missed (due to
a container restart, network timeout, or DeepFace server restart) the batch
sync will catch and ingest those detections within one sync interval.

Design decisions:
  - Reads DeepFace DB read-only (via a separate psycopg2 connection).
  - Uses a module-level "last_synced_at" watermark stored in memory.
    On process restart the watermark resets to (now - 2 * interval), so
    at most 2 intervals of events are re-processed.  The Neo4j DETECTED_IN
    CREATE is idempotent to duplicate frame_ids for the same entity/zone/ts
    because we check for an existing node first (MERGE on frame_id key).
  - Disabled by default in tests (DEEPFACE_BATCH_SYNC_INTERVAL_SECONDS=0).

Usage (called from main.py lifespan):
    import asyncio
    from services.deepface_batch_sync import DeepFaceBatchSync

    sync = DeepFaceBatchSync()
    asyncio.create_task(sync.run_forever())
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

import psycopg2
import psycopg2.extras

from config import settings
from services.cctv_graph_service import get_cctv_graph_service

logger = logging.getLogger(__name__)


class DeepFaceBatchSync:
    """
    Periodic reconciliation job that syncs DeepFace pgvector detections
    into the Neo4j graph.

    Reads from the `face_embeddings` table of the DeepFace Postgres instance
    (configurable via DEEPFACE_POSTGRES_URI).  Only rows with a created_at
    timestamp newer than the watermark are processed.
    """

    # Column names expected in the DeepFace face_embeddings table.
    # Adjust if the DeepFace server schema differs.
    TABLE = "face_embeddings"
    COL_LABEL = "img_name"        # = entity_id in our system
    COL_CREATED_AT = "created_at"
    COL_STREAM_ID = "stream_id"   # may be NULL for registered faces
    COL_ZONE_ID = "zone_id"       # may be NULL
    COL_FRAME_ID = "frame_id"     # may be NULL

    def __init__(self) -> None:
        self._last_synced_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run_forever(self) -> None:
        """
        Runs indefinitely, sleeping DEEPFACE_BATCH_SYNC_INTERVAL_SECONDS
        between each sync pass.

        Exits cleanly when the task is cancelled (e.g. on app shutdown).
        """
        interval = settings.DEEPFACE_BATCH_SYNC_INTERVAL_SECONDS
        if interval <= 0:
            logger.info("DeepFace batch sync disabled (interval=0)")
            return

        logger.info(
            "DeepFace batch sync started — interval=%ds postgres=%s",
            interval,
            settings.DEEPFACE_POSTGRES_URI.split("@")[-1],  # hide credentials
        )

        while True:
            try:
                await asyncio.sleep(interval)
                await self._sync_pass()
            except asyncio.CancelledError:
                logger.info("DeepFace batch sync task cancelled — shutting down")
                break
            except Exception as exc:  # pragma: no cover
                logger.error(
                    "DeepFace batch sync error (will retry next interval): %s",
                    exc,
                    exc_info=True,
                )

    # ------------------------------------------------------------------
    # Sync pass
    # ------------------------------------------------------------------

    async def _sync_pass(self) -> None:
        """Run one reconciliation pass in a thread pool executor."""
        loop = asyncio.get_running_loop()
        count = await loop.run_in_executor(None, self._sync_pass_sync)
        if count:
            logger.info("DeepFace batch sync: ingested %d new detection(s)", count)

    def _sync_pass_sync(self) -> int:
        """
        Synchronous core of the batch sync, executed in a thread pool
        so it does not block the asyncio event loop.

        Returns the number of detections successfully written to Neo4j.
        """
        interval = settings.DEEPFACE_BATCH_SYNC_INTERVAL_SECONDS
        now = datetime.now(timezone.utc)

        # On first run (or after restart), look back 2 intervals to catch
        # any events missed during startup.
        if self._last_synced_at is None:
            self._last_synced_at = now - timedelta(seconds=interval * 2)

        watermark = self._last_synced_at

        rows = self._fetch_new_detections(watermark)
        if not rows:
            logger.debug("DeepFace batch sync: no new rows since %s", watermark)
            self._last_synced_at = now
            return 0

        graph_svc = get_cctv_graph_service()
        written = 0

        for row in rows:
            entity_id: Optional[str] = row.get(self.COL_LABEL)
            zone_id: Optional[str] = row.get(self.COL_ZONE_ID)
            stream_id: Optional[str] = row.get(self.COL_STREAM_ID)
            frame_id: Optional[str] = row.get(self.COL_FRAME_ID)
            created_at: Optional[datetime] = row.get(self.COL_CREATED_AT)

            # Skip rows that lack the minimum fields to create a useful edge
            if not entity_id or not zone_id:
                logger.debug(
                    "Batch sync: skipping row — missing entity_id or zone_id: %s",
                    row,
                )
                continue

            ts = created_at if created_at else now

            # Ensure timezone-aware
            if isinstance(ts, datetime) and ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)

            # Check whether this detection already exists in Neo4j
            # (avoids duplicate edges on overlapping sync windows)
            if frame_id and self._detection_exists(graph_svc, entity_id, frame_id):
                continue

            try:
                graph_svc.create_detected_in(
                    entity_id=entity_id,
                    zone_id=zone_id,
                    timestamp=ts,
                    stream_id=stream_id or "batch_sync",
                    frame_id=frame_id,
                )
                written += 1
            except Exception as exc:
                logger.warning(
                    "Batch sync: failed to write detection entity=%s zone=%s: %s",
                    entity_id,
                    zone_id,
                    exc,
                )

        self._last_synced_at = now
        return written

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _fetch_new_detections(
        self, since: datetime
    ) -> List[Dict[str, Any]]:
        """
        Query the DeepFace pgvector database for rows created after `since`.

        Returns an empty list if the table does not exist or the connection
        fails (we don't want to crash the sync loop over a schema mismatch).
        """
        try:
            conn = psycopg2.connect(
                settings.DEEPFACE_POSTGRES_URI,
                cursor_factory=psycopg2.extras.RealDictCursor,
            )
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        f"""
                        SELECT img_name, created_at, stream_id, zone_id, frame_id
                        FROM {self.TABLE}
                        WHERE created_at > %s
                        ORDER BY created_at ASC
                        LIMIT 1000
                        """,
                        (since,),
                    )
                    return [dict(row) for row in cur.fetchall()]
        except psycopg2.errors.UndefinedTable:
            logger.debug(
                "DeepFace table '%s' does not exist yet — skipping batch sync pass",
                self.TABLE,
            )
            return []
        except Exception as exc:
            logger.warning(
                "DeepFace batch sync: DB query failed: %s", exc
            )
            return []

    @staticmethod
    def _detection_exists(graph_svc: Any, entity_id: str, frame_id: str) -> bool:
        """
        Return True if a DETECTED_IN relationship with this frame_id already
        exists in Neo4j for this entity.  Avoids writing duplicates on
        overlapping sync windows.
        """
        try:
            with graph_svc._driver.session() as session:
                result = session.run(
                    """
                    MATCH (e:Entity {entity_id: $entity_id})-[r:DETECTED_IN]->()
                    WHERE r.frame_id = $frame_id
                    RETURN count(r) AS cnt
                    """,
                    {"entity_id": entity_id, "frame_id": frame_id},
                )
                record = result.single()
                return bool(record and record["cnt"] > 0)
        except Exception:
            return False  # On error assume not exists — write is idempotent enough
