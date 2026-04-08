"""
Reset entity data — removes all entity_profiles and entity_identifiers rows.

Usage (from inside backend container):
    python scripts/reset_entity_data.py --confirm

Or via docker compose:
    docker compose -f docker-compose.prod.yml exec backend python scripts/reset_entity_data.py --confirm
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reset all entity data from the database.")
    parser.add_argument(
        "--confirm",
        action="store_true",
        help="Required flag to confirm data deletion.",
    )
    args = parser.parse_args()

    if not args.confirm:
        logger.error("Pass --confirm to proceed. This will delete ALL entity data.")
        sys.exit(1)

    try:
        from database.connection import SessionLocal
        from models.db.entity_identifiers import EntityIdentifier
        from models.db.entity_profiles import EntityProfile
    except ImportError as exc:
        logger.error("Import failed: %s — run from the backend directory.", exc)
        sys.exit(1)

    with SessionLocal() as db:
        try:
            ident_count = db.query(EntityIdentifier).delete()
            profile_count = db.query(EntityProfile).delete()
            db.commit()
            logger.info("Deleted %d entity_identifiers and %d entity_profiles.", ident_count, profile_count)
        except Exception as exc:
            db.rollback()
            logger.error("Reset failed: %s", exc)
            sys.exit(1)


if __name__ == "__main__":
    main()
