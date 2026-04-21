"""
Idempotent migration: add organization_id column to all org-scoped tables
and backfill existing rows with 'default-org'.

Run:
    python migrations/add_organization_id.py
    python migrations/add_organization_id.py --dry-run   # print SQL only
"""

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database.connection import engine

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

# Tables that get nullable=False + default='default-org'
TABLES_NOT_NULL = [
    "alerts",
    "staff_profiles",
    "alert_assignments",
    "alert_audit_logs",
    "notification_queue",
    "notification_logs",
    "camera_streams",
    "outgoing_webhooks",
    "push_subscriptions",
    "entity_profiles",
    "entity_identifiers",
]

# sensor_events stays nullable — pollers need to be updated before enforcing NOT NULL
TABLES_NULLABLE = [
    "sensor_events",
]

# Composite indexes for the hot query paths (all IF NOT EXISTS — safe to re-run)
INDEXES = [
    "CREATE INDEX IF NOT EXISTS ix_alerts_org_status       ON alerts            (organization_id, status);",
    "CREATE INDEX IF NOT EXISTS ix_alerts_org_created      ON alerts            (organization_id, created_at);",
    "CREATE INDEX IF NOT EXISTS ix_staff_org_duty          ON staff_profiles     (organization_id, on_duty);",
    "CREATE INDEX IF NOT EXISTS ix_cameras_org_status      ON camera_streams     (organization_id, status);",
    "CREATE INDEX IF NOT EXISTS ix_sensor_events_org_ts    ON sensor_events      (organization_id, timestamp);",
    "CREATE INDEX IF NOT EXISTS ix_entity_profiles_org     ON entity_profiles    (organization_id);",
    "CREATE INDEX IF NOT EXISTS ix_entity_idents_org_type  ON entity_identifiers (organization_id, identifier_type, identifier_value);",
]


def run(dry_run: bool = False) -> None:
    if dry_run:
        logger.info("DRY RUN — printing SQL only, nothing will be executed.")

    statements = []

    # ── 1. Add column (nullable first so existing rows aren't rejected) ──────
    for table in TABLES_NOT_NULL:
        statements.append(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS organization_id VARCHAR;"
        )
    for table in TABLES_NULLABLE:
        statements.append(
            f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS organization_id VARCHAR;"
        )

    # ── 2. Backfill existing rows ────────────────────────────────────────────
    for table in TABLES_NOT_NULL + TABLES_NULLABLE:
        statements.append(
            f"UPDATE {table} SET organization_id = 'default-org' WHERE organization_id IS NULL;"
        )

    # ── 3. Add NOT NULL constraint for the non-nullable tables ──────────────
    #    Separate ALTER so sensor_events stays nullable.
    for table in TABLES_NOT_NULL:
        statements.append(
            f"ALTER TABLE {table} ALTER COLUMN organization_id SET NOT NULL;"
        )
    for table in TABLES_NOT_NULL:
        statements.append(
            f"ALTER TABLE {table} ALTER COLUMN organization_id SET DEFAULT 'default-org';"
        )

    # ── 4. Indexes ───────────────────────────────────────────────────────────
    statements.extend(INDEXES)

    if dry_run:
        for stmt in statements:
            print(stmt)
        return

    with engine.begin() as conn:
        for stmt in statements:
            logger.info("Executing: %s", stmt[:80] + ("…" if len(stmt) > 80 else ""))
            conn.execute(text(stmt))

    logger.info(
        "Migration complete — organization_id added to %d tables, %d indexes verified.",
        len(TABLES_NOT_NULL) + len(TABLES_NULLABLE),
        len(INDEXES),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Add organization_id to all org-scoped tables")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print SQL statements without executing them",
    )
    args = parser.parse_args()
    run(dry_run=args.dry_run)
