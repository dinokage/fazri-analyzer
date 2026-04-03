"""
Event Ingestion Service — single entry point for all sensor data.

Every RFID swipe, WiFi association event, and camera face match flows through
this service before reaching the database, graph, or alert pipeline.

Pipeline (per event):
    1. Entity resolution (identifier → entity_id)
    2. Persist to sensor_events table
    3. If CAMERA event: run anomaly detection
    4. If anomaly detected: create alert via AlertService
    5. Project event to Neo4j DETECTED_IN graph (fire-and-forget, non-blocking)
    6. Return ResolvedEvent (or raw SensorEvent if unresolvable)

Usage
-----
    from services.event_ingestion_service import get_event_ingestion_service

    svc = await get_event_ingestion_service(db)
    result = await svc.ingest(sensor_event)
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from config.zone_matrix import zone_matrix
from models.db.sensor_events import SensorEventRecord
from models.schemas.sensor_events import EventType, ResolvedEvent, SensorEvent, SensorType
from services.entity_resolution_service import (
    EntityProfileDTO,
    EntityResolutionService,
    get_entity_resolution_service,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy imports — avoid circular dependencies and optional heavy deps
# ---------------------------------------------------------------------------


def _get_anomaly_analyzer():
    from services.deepface_anomaly import DeepFaceAnomalyAnalyzer
    return DeepFaceAnomalyAnalyzer


def _get_alert_service(db: Session):
    from services.alerts.alert_service import AlertService
    return AlertService(db)


def _get_cctv_graph_service():
    from services.cctv_graph_service import get_cctv_graph_service
    return get_cctv_graph_service()


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EventIngestionService:
    """
    Receives normalised SensorEvents, resolves entities, persists, and
    triggers downstream anomaly detection and graph projection.

    Parameters
    ----------
    db:
        An open SQLAlchemy session.  The caller is responsible for commit/close.
    entity_resolver:
        EntityResolutionService instance (uses module singleton by default).
    """

    def __init__(
        self,
        db: Session,
        entity_resolver: Optional[EntityResolutionService] = None,
    ) -> None:
        self.db = db
        self.resolver = entity_resolver or get_entity_resolution_service()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest(self, event: SensorEvent) -> Optional[ResolvedEvent]:
        """
        Ingest a single normalised SensorEvent through the full pipeline.

        Returns a ResolvedEvent when the identifier could be mapped to a
        known entity, otherwise returns None (event still gets persisted).
        """
        # Step 1: Entity resolution
        profile = self.resolver.resolve(
            identifier_type=event.identifier_type,
            identifier_value=event.raw_identifier,
            db=self.db,
        )

        resolved: Optional[ResolvedEvent] = None
        if profile is not None:
            resolved = ResolvedEvent(
                **event.model_dump(exclude={"resolved_entity_id"}),
                resolved_entity_id=profile.entity_id,
                entity_name=profile.name,
                entity_role=profile.role,
                entity_department=profile.department,
            )
            log_name = profile.name or profile.entity_id
            logger.info(
                "Event %s resolved → %s (%s) zone=%s",
                event.event_id,
                log_name,
                event.sensor_type,
                event.zone_id,
            )
        else:
            logger.info(
                "Event %s unresolved — identifier_type=%s value=%s zone=%s",
                event.event_id,
                event.identifier_type,
                event.raw_identifier,
                event.zone_id,
            )

        # Step 2: Persist to sensor_events
        self._persist(resolved or event)

        if resolved is None:
            return None

        # Step 3 + 4: Anomaly detection & alerting (CAMERA events only)
        if event.sensor_type == SensorType.CAMERA:
            await self._run_anomaly_detection(resolved, profile)

        # Step 5: Neo4j graph projection (fire-and-forget)
        asyncio.create_task(self._project_to_graph(resolved))

        return resolved

    async def ingest_batch(
        self, events: List[SensorEvent]
    ) -> List[Optional[ResolvedEvent]]:
        """
        Ingest a list of SensorEvents sequentially.

        Order is preserved so that impossible-travel detection sees events in
        the correct chronological sequence.
        """
        results: List[Optional[ResolvedEvent]] = []
        for event in events:
            result = await self.ingest(event)
            results.append(result)
        return results

    # ------------------------------------------------------------------
    # Internal pipeline steps
    # ------------------------------------------------------------------

    def _persist(self, event: SensorEvent) -> None:
        """Write the event to the sensor_events table."""
        metadata = dict(event.metadata) if event.metadata else {}
        record = SensorEventRecord(
            event_id=event.event_id,
            sensor_type=event.sensor_type.value,
            event_type=event.event_type.value,
            timestamp=event.timestamp,
            zone_id=event.zone_id,
            raw_identifier=event.raw_identifier,
            identifier_type=event.identifier_type,
            resolved_entity_id=getattr(event, "resolved_entity_id", None),
            confidence=event.confidence,
            source_device_id=event.source_device_id,
            building=event.building,
            floor=event.floor,
            raw_payload=event.raw_payload,
            metadata_=metadata,
        )
        self.db.add(record)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    async def _run_anomaly_detection(
        self,
        resolved: ResolvedEvent,
        profile: EntityProfileDTO,
    ) -> None:
        """Run anomaly rules and create an alert if one fires."""
        try:
            # Fetch recent detections for this entity (last 30 minutes)
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
            rows = (
                self.db.query(SensorEventRecord)
                .filter(
                    SensorEventRecord.resolved_entity_id == resolved.resolved_entity_id,
                    SensorEventRecord.sensor_type == SensorType.CAMERA.value,
                    SensorEventRecord.timestamp >= cutoff,
                )
                .order_by(SensorEventRecord.timestamp.desc())
                .limit(20)
                .all()
            )

            recent_detections = [
                {"zone_id": r.zone_id, "timestamp": r.timestamp}
                for r in rows
            ]

            entity_dict = {
                "entity_id": resolved.resolved_entity_id,
                "name": resolved.entity_name,
                "role": resolved.entity_role,
            }

            # Build match dict mimicking a deepface match (confidence already scaled)
            match_dict = {
                "img_name": resolved.raw_identifier,
                "distance": 1.0 - resolved.confidence,
                "confidence": resolved.confidence * 100,
                "threshold": 0.60,
            }

            authorized_zones = self.resolver.get_authorized_zones(
                resolved.resolved_entity_id, db=self.db
            )

            analyzer = _get_anomaly_analyzer()
            anomaly = analyzer.analyze(
                match=match_dict,
                entity=entity_dict,
                zone_id=resolved.zone_id,
                authorized_zones=authorized_zones,
                recent_detections=recent_detections,
                alert_on_unknown_face=True,
            )

            if anomaly:
                logger.info(
                    "Anomaly detected for %s in zone %s: %s",
                    resolved.resolved_entity_id,
                    resolved.zone_id,
                    anomaly["anomaly_type"],
                )
                await self._create_alert(resolved, anomaly)

        except Exception as exc:
            logger.error("Anomaly detection failed for %s: %s", resolved.event_id, exc)

    async def _create_alert(
        self,
        resolved: ResolvedEvent,
        anomaly: dict,
    ) -> None:
        """
        Create an alert from a fired anomaly rule.

        Uses the shared Redis cooldown gate to prevent duplicate alerts for
        the same (anomaly_type, source_device, entity) within the cooldown window.
        """
        from services.alert_cooldown import set_alert_cooldown, delete_alert_cooldown

        anomaly_type = anomaly["anomaly_type"]
        source_device = resolved.source_device_id or resolved.zone_id
        entity_key = resolved.resolved_entity_id

        # Atomic cooldown gate — returns True only when freshly created
        if not set_alert_cooldown(anomaly_type, source_device, entity_key):
            logger.info(
                "Alert suppressed (cooldown): %s source=%s entity=%s",
                anomaly_type,
                source_device,
                entity_key,
            )
            return

        try:
            from models.schemas.alerts import AlertCreate, AlertSeverityEnum, LocationSchema
            from models.db.alerts import ActorType

            severity_map = {
                "critical": AlertSeverityEnum.CRITICAL,
                "high": AlertSeverityEnum.HIGH,
                "medium": AlertSeverityEnum.MEDIUM,
                "low": AlertSeverityEnum.LOW,
            }
            severity = severity_map.get(
                anomaly.get("severity", "medium"), AlertSeverityEnum.MEDIUM
            )

            alert_data = AlertCreate(
                anomaly_id=str(uuid.uuid4()),
                anomaly_type=anomaly_type,
                title=(
                    f"Sensor Alert: {anomaly_type.replace('_', ' ').title()}"
                ),
                description=anomaly["description"],
                severity=severity,
                location=LocationSchema(
                    zone_id=resolved.zone_id,
                    building=resolved.building,
                    floor=resolved.floor,
                ),
                affected_entities=[resolved.resolved_entity_id],
                data_sources=[resolved.sensor_type.value],
                evidence={
                    "sensor_type": resolved.sensor_type.value,
                    "event_id": resolved.event_id,
                    "confidence": resolved.confidence,
                    "anomaly_details": anomaly.get("details", {}),
                },
                is_mock=False,
            )

            alert_svc = _get_alert_service(self.db)
            alert = alert_svc.create_alert(
                alert_data=alert_data,
                actor_type=ActorType.SYSTEM,
            )
            logger.info("Alert created: id=%s type=%s", alert.id, anomaly_type)

            # Dispatch outgoing webhook if configured
            try:
                from services.webhook_service import WebhookService
                wh_svc = WebhookService(self.db)
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: wh_svc.dispatch_alert(alert),
                )
            except Exception as wh_exc:
                logger.warning("Webhook dispatch failed: %s", wh_exc)

        except Exception as exc:
            # Release cooldown so the alert can be retried next time
            delete_alert_cooldown(anomaly_type, source_device, entity_key)
            logger.error("Alert creation failed: %s", exc)

    async def _project_to_graph(self, resolved: ResolvedEvent) -> None:
        """
        Project a resolved event to Neo4j as a DETECTED_IN relationship.

        Runs in a background task — failures here do not affect the event
        pipeline.  Uses CctvGraphService.create_detected_in() for camera
        events and a generic Entity→Zone merge for other sensor types.
        """
        try:
            graph_svc = _get_cctv_graph_service()

            if resolved.sensor_type == SensorType.CAMERA:
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: graph_svc.create_detected_in(
                        entity_id=resolved.resolved_entity_id,
                        zone_id=resolved.zone_id,
                        timestamp=resolved.timestamp,
                        stream_id=resolved.source_device_id or "unknown",
                        face_id=resolved.raw_identifier,
                        frame_id=resolved.event_id,
                    ),
                )
            else:
                # Generic sensor event projection
                await asyncio.get_running_loop().run_in_executor(
                    None,
                    lambda: graph_svc.project_sensor_event(
                        entity_id=resolved.resolved_entity_id,
                        zone_id=resolved.zone_id,
                        timestamp=resolved.timestamp,
                        sensor_type=resolved.sensor_type.value,
                        event_id=resolved.event_id,
                    ),
                )
        except AttributeError:
            # project_sensor_event may not exist yet — CCTV path covers Week 2
            logger.debug(
                "Neo4j projection skipped for sensor_type=%s (method not found)",
                resolved.sensor_type,
            )
        except Exception as exc:
            logger.warning(
                "Neo4j projection failed for event %s: %s — continuing",
                resolved.event_id,
                exc,
            )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def get_event_ingestion_service(db: Session) -> EventIngestionService:
    """Create an EventIngestionService bound to the given database session."""
    return EventIngestionService(db=db)
