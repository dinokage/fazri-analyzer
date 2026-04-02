"""
Idempotent migration: create entity_identifiers and entity_profiles tables,
enable pg_trgm for fuzzy name search, and seed from existing CSV data.

Run:
    python migrations/create_entity_tables.py
    python migrations/create_entity_tables.py --seed   # also seed from CSV
    python migrations/create_entity_tables.py --seed --csv path/to/profiles.csv
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


DDL_ENTITY_PROFILES = """
CREATE TABLE IF NOT EXISTS entity_profiles (
    entity_id       VARCHAR     NOT NULL,
    name            VARCHAR     NULL,
    role            VARCHAR     NULL,
    email           VARCHAR     NULL,
    department      VARCHAR     NULL,
    authorized_zones JSONB      NOT NULL DEFAULT '[]',
    metadata        JSONB       NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_entity_profiles PRIMARY KEY (entity_id)
);
"""

DDL_ENTITY_IDENTIFIERS = """
CREATE TABLE IF NOT EXISTS entity_identifiers (
    id              UUID        NOT NULL DEFAULT uuid_generate_v4(),
    entity_id       VARCHAR     NOT NULL,
    identifier_type VARCHAR     NOT NULL,
    identifier_value VARCHAR    NOT NULL,
    source          VARCHAR     NOT NULL DEFAULT 'manual',
    confidence      FLOAT       NOT NULL DEFAULT 1.0,
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    active          BOOLEAN     NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT pk_entity_identifiers PRIMARY KEY (id),
    CONSTRAINT uq_entity_identifiers_type_value
        UNIQUE (identifier_type, identifier_value)
);
"""

DDL_INDEXES = [
    # entity_profiles
    "CREATE INDEX IF NOT EXISTS ix_entity_profiles_email    ON entity_profiles (email);",
    # GIN trigram index for fuzzy name search
    "CREATE INDEX IF NOT EXISTS ix_entity_profiles_name_trgm ON entity_profiles USING gin (name gin_trgm_ops);",
    # entity_identifiers
    "CREATE INDEX IF NOT EXISTS ix_entity_identifiers_entity_id   ON entity_identifiers (entity_id);",
    "CREATE INDEX IF NOT EXISTS ix_entity_identifiers_type        ON entity_identifiers (identifier_type);",
    "CREATE INDEX IF NOT EXISTS ix_entity_identifiers_value       ON entity_identifiers (identifier_value);",
    "CREATE INDEX IF NOT EXISTS ix_entity_identifiers_type_value  ON entity_identifiers (identifier_type, identifier_value);",
]


def run(seed: bool = False, csv_path: Optional[str] = None) -> None:
    logger.info("Running entity tables migration…")

    with engine.begin() as conn:
        conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp";'))
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        logger.info("Extensions: uuid-ossp + pg_trgm OK")

        conn.execute(text(DDL_ENTITY_PROFILES))
        logger.info("Table entity_profiles: OK")

        conn.execute(text(DDL_ENTITY_IDENTIFIERS))
        logger.info("Table entity_identifiers: OK")

        for ddl in DDL_INDEXES:
            conn.execute(text(ddl))
        logger.info("Indexes: OK (%d verified)", len(DDL_INDEXES))

    logger.info("Schema migration complete.")

    if seed:
        _seed_from_csv(csv_path)


def _seed_from_csv(csv_path: Optional[str]) -> None:
    if csv_path is None:
        # Default to the bundled augmented data
        here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        csv_path = os.path.join(here, "augmented", "student_staff_profiles.csv")

    if not os.path.exists(csv_path):
        logger.warning("CSV not found at %s — skipping seed.", csv_path)
        return

    from services.entity_resolution_service import get_entity_resolution_service

    svc = get_entity_resolution_service()
    stats = svc.bulk_import_from_csv(csv_path)
    logger.info(
        "Seed complete: created=%d updated=%d skipped=%d",
        stats["created"],
        stats["updated"],
        stats["skipped"],
    )


# ---------------------------------------------------------------------------
# Allow Optional import at module level
# ---------------------------------------------------------------------------
from typing import Optional  # noqa: E402 — after sys.path setup

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create entity tables")
    parser.add_argument(
        "--seed",
        action="store_true",
        help="Seed from augmented/student_staff_profiles.csv after migration",
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=None,
        help="Path to CSV file for seeding (overrides default)",
    )
    args = parser.parse_args()
    run(seed=args.seed, csv_path=args.csv_path)
