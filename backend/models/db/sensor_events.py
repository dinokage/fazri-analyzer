"""
SQLAlchemy model for persisting sensor events in PostgreSQL.

Every sensor event — RFID card swipe, WiFi association, camera face match —
is normalised to a SensorEvent Pydantic schema and then persisted here.
This table is the source of truth for all sensor data in FAZRI.
"""

import uuid

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Index,
    JSON,
    String,
)
from sqlalchemy.dialects.postgresql import UUID

from database.connection import Base


class SensorEventRecord(Base):
    """
    Persistent record of a normalised sensor event.

    Columns mirror the ``SensorEvent`` Pydantic schema from
    ``models/schemas/sensor_events.py``.  Enum values are stored as plain
    strings so the table never needs an ALTER when a new sensor type is added.
    """

    __tablename__ = "sensor_events"

    # ------------------------------------------------------------------
    # Primary key
    # ------------------------------------------------------------------

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("uuid_generate_v4()"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Deduplication — event_id is the stable application-level identifier
    # ------------------------------------------------------------------

    event_id = Column(String, unique=True, index=True, nullable=False)

    # ------------------------------------------------------------------
    # Sensor / event classification
    # ------------------------------------------------------------------

    sensor_type = Column(String, index=True, nullable=False)
    event_type = Column(String, nullable=False)

    # ------------------------------------------------------------------
    # Temporal and spatial
    # ------------------------------------------------------------------

    timestamp = Column(DateTime(timezone=True), index=True, nullable=False)
    zone_id = Column(String, index=True, nullable=False)

    # ------------------------------------------------------------------
    # Identifier fields
    # ------------------------------------------------------------------

    raw_identifier = Column(String, index=True, nullable=False)
    identifier_type = Column(String, nullable=False)

    # Filled by EntityResolutionService after initial persistence
    resolved_entity_id = Column(String, index=True, nullable=True)

    # ------------------------------------------------------------------
    # Quality / provenance
    # ------------------------------------------------------------------

    confidence = Column(Float, default=1.0, nullable=False)
    source_device_id = Column(String, nullable=True)

    # ------------------------------------------------------------------
    # Optional location refinement
    # ------------------------------------------------------------------

    building = Column(String, nullable=True)
    floor = Column(String, nullable=True)

    # ------------------------------------------------------------------
    # Debugging payload and extensible metadata
    # ------------------------------------------------------------------

    raw_payload = Column(JSON, nullable=True)
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    # ------------------------------------------------------------------
    # Audit
    # ------------------------------------------------------------------

    created_at = Column(
        DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )

    # ------------------------------------------------------------------
    # Composite indexes
    # Three access patterns drive these:
    #   1. Zone event feed (zone + time window)
    #   2. Entity timeline (entity + time window)
    #   3. Source-filtered queries (sensor_type + time window)
    # ------------------------------------------------------------------

    __table_args__ = (
        Index("ix_sensor_events_zone_ts", "zone_id", "timestamp"),
        Index("ix_sensor_events_entity_ts", "resolved_entity_id", "timestamp"),
        Index("ix_sensor_events_sensor_type_ts", "sensor_type", "timestamp"),
    )

    def __repr__(self) -> str:
        return (
            f"<SensorEventRecord {self.event_id} "
            f"sensor={self.sensor_type} zone={self.zone_id} "
            f"entity={self.resolved_entity_id}>"
        )
