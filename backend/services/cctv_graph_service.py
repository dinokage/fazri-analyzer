"""
CCTV Graph Service.

Wraps all Neo4j read/write operations specific to real-time face-detection
events coming from RTSP camera streams via the DeepFace server.

The DETECTED_IN relationship and its properties mirror the batch ingestion
pattern in scripts/ingest_real_data.py _ingest_cctv_frames(), with two
additions:
  - stream_id: identifies the physical camera (e.g. "cam-01")
  - source: "deepface_rtsp"  (distinguishes live events from batch ingest)

Usage:
    svc = get_cctv_graph_service()
    entity = svc.get_entity_by_entity_id("ENT-001")
    svc.create_detected_in(
        entity_id="ENT-001",
        zone_id="LAB_101",
        timestamp=datetime.utcnow(),
        frame_id="cam-01-frame-0042",
        face_id="ENT-001",
        stream_id="cam-01",
    )
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from neo4j import GraphDatabase, Driver

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_cctv_graph_service: Optional["CctvGraphService"] = None


def get_cctv_graph_service() -> "CctvGraphService":
    """Return (or lazily create) the module-level CctvGraphService singleton."""
    global _cctv_graph_service
    if _cctv_graph_service is None:
        _cctv_graph_service = CctvGraphService(
            uri=settings.NEO4J_URI,
            user=settings.NEO4J_USER,
            password=settings.NEO4J_PASSWORD,
        )
        logger.info("CctvGraphService initialised — uri=%s", settings.NEO4J_URI)
    return _cctv_graph_service


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class CctvGraphService:
    """
    Neo4j helper for real-time CCTV face-detection events.

    All public methods are synchronous (the Neo4j Python driver manages its
    own thread pool) so they can be called directly from async FastAPI
    handlers via run_in_executor or simply awaited in a thread-safe manner
    without blocking the event loop for long-running queries.  For the
    current throughput (one webhook per match, not thousands per second)
    calling them synchronously inside async handlers is acceptable.
    """

    def __init__(self, uri: str, user: str, password: str) -> None:
        self._driver: Driver = GraphDatabase.driver(
            uri, auth=(user, password)
        )

    # ------------------------------------------------------------------
    # Entity lookup
    # ------------------------------------------------------------------

    def get_entity_by_entity_id(self, entity_id: str) -> Optional[Dict[str, Any]]:
        """
        Return a dict of entity properties for the given entity_id, or None
        if no such entity exists in the graph.

        Example return value:
            {
                "entity_id": "ENT-001",
                "name": "Alice Johnson",
                "role": "STUDENT",
                "department": "Computer Science",
                "face_id": "ENT-001",
                ...
            }
        """
        query = """
            MATCH (e:Entity {entity_id: $entity_id})
            RETURN e
        """
        with self._driver.session() as session:
            result = session.run(query, {"entity_id": entity_id})
            record = result.single()
            if record is None:
                return None
            return dict(record["e"])

    def get_authorized_zones(self, entity_id: str) -> List[str]:
        """
        Return the list of zone_ids the entity is permitted to be in.

        The authorisation is derived from ACCESS_PERMISSION relationships in
        the graph (set during entity registration / data ingestion).  If no
        explicit permissions exist, an empty list is returned so callers can
        treat it as "no restrictions" or "all denied" depending on context.
        """
        query = """
            MATCH (e:Entity {entity_id: $entity_id})-[:HAS_ACCESS]->(z:Zone)
            RETURN z.zone_id AS zone_id
        """
        with self._driver.session() as session:
            result = session.run(query, {"entity_id": entity_id})
            return [record["zone_id"] for record in result]

    # ------------------------------------------------------------------
    # Detection write
    # ------------------------------------------------------------------

    def create_detected_in(
        self,
        entity_id: str,
        zone_id: str,
        timestamp: datetime,
        stream_id: str,
        face_id: Optional[str] = None,
        frame_id: Optional[str] = None,
    ) -> None:
        """
        Create a DETECTED_IN relationship between an Entity and a Zone.

        Mirrors the Cypher pattern in scripts/ingest_real_data.py
        _ingest_cctv_frames() (lines 226-236) with the addition of
        stream_id and source fields for live-event traceability.

        A unique frame_id is auto-generated when not provided (webhook
        payloads do not always include a frame number).

        The Zone node is expected to already exist; if it does not, the
        CREATE is silently skipped because the MATCH will return no rows.
        Log a warning when the entity or zone cannot be found.
        """
        # Normalise timestamp to ISO-8601 string for Neo4j datetime()
        ts_str = (
            timestamp.astimezone(timezone.utc).isoformat()
            if timestamp.tzinfo
            else timestamp.isoformat() + "Z"
        )

        if frame_id is None:
            # Deterministic ID so retries MERGE onto the same relationship
            # instead of creating duplicate edges.
            frame_id = hashlib.md5(
                f"{stream_id}:{entity_id}:{ts_str}".encode()
            ).hexdigest()[:16]

        query = """
            MATCH (e:Entity {entity_id: $entity_id})
            MATCH (z:Zone {zone_id: $zone_id})
            MERGE (e)-[r:DETECTED_IN {frame_id: $frame_id}]->(z)
            ON CREATE SET
                r.timestamp   = datetime($timestamp),
                r.face_id     = $face_id,
                r.location_id = $zone_id,
                r.stream_id   = $stream_id,
                r.source      = "deepface_rtsp"
            ON MATCH SET
                r.timestamp   = datetime($timestamp),
                r.face_id     = $face_id,
                r.location_id = $zone_id,
                r.stream_id   = $stream_id,
                r.source      = "deepface_rtsp"
        """
        params = {
            "entity_id": entity_id,
            "zone_id": zone_id,
            "timestamp": ts_str,
            "frame_id": frame_id,
            "face_id": face_id or entity_id,
            "stream_id": stream_id,
        }

        with self._driver.session() as session:
            result = session.run(query, params)
            summary = result.consume()
            if summary.counters.relationships_created == 0:
                # 0 can mean the relationship already existed (idempotent MERGE)
                # OR the entity/zone node was not found. Both are non-fatal.
                logger.debug(
                    "create_detected_in: relationship already existed or "
                    "entity_id=%s / zone_id=%s not found in graph",
                    entity_id,
                    zone_id,
                )
            else:
                logger.debug(
                    "DETECTED_IN created: entity=%s zone=%s stream=%s",
                    entity_id,
                    zone_id,
                    stream_id,
                )

    def create_unknown_detected_in(
        self,
        zone_id: str,
        timestamp: datetime,
        stream_id: str,
        frame_id: Optional[str] = None,
    ) -> None:
        """
        Log an unknown-face detection event against a zone (no entity match).

        Creates a lightweight UNKNOWN_FACE_DETECTED event node linked to the
        zone for audit purposes without touching entity nodes.
        """
        ts_str = (
            timestamp.astimezone(timezone.utc).isoformat()
            if timestamp.tzinfo
            else timestamp.isoformat() + "Z"
        )

        if frame_id is None:
            frame_id = hashlib.md5(
                f"{stream_id}:unknown:{zone_id}:{ts_str}".encode()
            ).hexdigest()[:16]

        query = """
            MATCH (z:Zone {zone_id: $zone_id})
            MERGE (ev:UnknownFaceEvent {frame_id: $frame_id})
            ON CREATE SET
                ev.zone_id   = $zone_id,
                ev.stream_id = $stream_id,
                ev.timestamp = datetime($timestamp),
                ev.source    = "deepface_rtsp"
            ON MATCH SET
                ev.zone_id   = $zone_id,
                ev.stream_id = $stream_id,
                ev.timestamp = datetime($timestamp),
                ev.source    = "deepface_rtsp"
            MERGE (ev)-[:DETECTED_IN]->(z)
        """
        params = {
            "zone_id": zone_id,
            "frame_id": frame_id,
            "stream_id": stream_id,
            "timestamp": ts_str,
        }
        with self._driver.session() as session:
            session.run(query, params)

    # ------------------------------------------------------------------
    # Recent-detection queries (for anomaly analysis)
    # ------------------------------------------------------------------

    def get_recent_detections(
        self,
        entity_id: str,
        minutes: int = 60,
    ) -> List[Dict[str, Any]]:
        """
        Return all DETECTED_IN events for entity_id within the last N minutes.

        Each dict contains: zone_id, stream_id, timestamp (datetime), frame_id.
        Used by DeepFaceAnomalyAnalyzer to detect impossible-travel patterns.
        """
        query = """
            MATCH (e:Entity {entity_id: $entity_id})-[r:DETECTED_IN]->(z:Zone)
            WHERE r.timestamp >= datetime() - duration({minutes: $minutes})
              AND r.source = "deepface_rtsp"
            RETURN z.zone_id AS zone_id,
                   r.stream_id  AS stream_id,
                   r.timestamp  AS timestamp,
                   r.frame_id   AS frame_id
            ORDER BY r.timestamp DESC
        """
        with self._driver.session() as session:
            result = session.run(
                query, {"entity_id": entity_id, "minutes": minutes}
            )
            return [
                {
                    "zone_id": rec["zone_id"],
                    "stream_id": rec["stream_id"],
                    "timestamp": rec["timestamp"],
                    "frame_id": rec["frame_id"],
                }
                for rec in result
            ]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def close(self) -> None:
        """Close the underlying Neo4j driver."""
        self._driver.close()
