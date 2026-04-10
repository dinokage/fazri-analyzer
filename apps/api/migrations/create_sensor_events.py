"""
Idempotent migration: create the sensor_events table and its indexes.

Run directly:
    python -m backend.migrations.create_sensor_events

Or from the backend directory:
    python migrations/create_sensor_events.py

The script is safe to run multiple times — it uses CREATE TABLE IF NOT EXISTS
and CREATE INDEX IF NOT EXISTS so it never fails on an already-migrated DB.
"""

import logging
import sys
import os

# Allow running as a script from the backend directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from database.connection import engine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


DDL_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS sensor_events (
    id              UUID        NOT NULL DEFAULT uuid_generate_v4(),
    event_id        VARCHAR     NOT NULL,
    sensor_type     VARCHAR     NOT NULL,
    event_type      VARCHAR     NOT NULL,
    timestamp       TIMESTAMPTZ NOT NULL,
    zone_id         VARCHAR     NOT NULL,
    raw_identifier  VARCHAR     NOT NULL,
    identifier_type VARCHAR     NOT NULL,
    resolved_entity_id VARCHAR  NULL,
    confidence      FLOAT       NOT NULL DEFAULT 1.0,
    source_device_id VARCHAR    NULL,
    building        VARCHAR     NULL,
    floor           VARCHAR     NULL,
    raw_payload     JSONB       NULL,
    metadata        JSONB       NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_sensor_events PRIMARY KEY (id),
    CONSTRAINT uq_sensor_events_event_id UNIQUE (event_id)
);
"""

DDL_INDEXES = [
    # Single-column indexes (covering the most common lookups)
    # ix_sensor_events_event_id intentionally omitted: the UNIQUE constraint
    # uq_sensor_events_event_id already creates a B-tree index on event_id.
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_sensor_type       ON sensor_events (sensor_type);",
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_timestamp         ON sensor_events (timestamp);",
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_zone_id           ON sensor_events (zone_id);",
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_raw_identifier    ON sensor_events (raw_identifier);",
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_resolved_entity   ON sensor_events (resolved_entity_id);",
    # Composite indexes for the three main query patterns
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_zone_ts           ON sensor_events (zone_id, timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_entity_ts         ON sensor_events (resolved_entity_id, timestamp DESC);",
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_sensor_type_ts    ON sensor_events (sensor_type, timestamp DESC);",
]


def run() -> None:
    """Create the sensor_events table and all associated indexes."""
    logger.info("Running sensor_events migration…")

    with engine.begin() as conn:
        # Ensure uuid_generate_v4 is available
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        logger.info("Extension uuid-ossp: OK")

        conn.execute(text(DDL_CREATE_TABLE))
        logger.info("Table sensor_events: OK")

        for ddl in DDL_INDEXES:
            conn.execute(text(ddl))

        logger.info("Indexes: OK (%d created/verified)", len(DDL_INDEXES))

    logger.info("Migration complete.")


if __name__ == "__main__":
    run()
