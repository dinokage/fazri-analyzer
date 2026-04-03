"""
SAP CSV Import Tool.

Reads a CSV export from SAP and creates entity_profiles + entity_identifiers
records in PostgreSQL.  Safe to run multiple times — all writes are upserts.

Usage
-----
    # Import with default SAP column mapping
    python scripts/sap_csv_import.py augmented/student_staff_profiles.csv

    # Preview what would be imported
    python scripts/sap_csv_import.py augmented/student_staff_profiles.csv --dry-run

    # Custom batch size
    python scripts/sap_csv_import.py data.csv --batch-size 200

    # Custom column mapping (JSON)
    python scripts/sap_csv_import.py data.csv --mapping '{"empNo":"entity_id","fullName":"name"}'
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import os
import sys
from typing import Dict, List, Optional

# Allow running directly from the backend directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Default column mapping: SAP CSV column → FAZRI field
# ---------------------------------------------------------------------------
DEFAULT_COLUMN_MAP: Dict[str, str] = {
    # Profile fields
    "entity_id":      "entity_id",
    "employee_no":    "entity_id",   # SAP employee number maps to entity_id
    "name":           "name",
    "designation":    "role",
    "role":           "role",
    "department":     "department",
    "email":          "email",
    # Identifier fields (value → identifier_type in entity_identifiers)
    "card_number":    "card_id",
    "card_id":        "card_id",
    "student_id":     "student_id",
    "staff_id":       "staff_id",
    "device_hash":    "mac_address",
    "face_id":        "face_id",
}

# Columns that become entity_identifiers rows (fazri_field_name → identifier_type)
IDENTIFIER_COLUMNS = {
    "card_id":    "card_id",
    "student_id": "student_id",
    "staff_id":   "staff_id",
    "mac_address": "mac_address",
    "face_id":    "face_id",
    "email":      "email",
}


def _apply_mapping(row: Dict[str, str], mapping: Dict[str, str]) -> Dict[str, str]:
    """Map raw CSV row fields to FAZRI field names using the column mapping."""
    out: Dict[str, str] = {}
    for col, value in row.items():
        fazri_field = mapping.get(col.strip().lower())
        if fazri_field and value.strip():
            out[fazri_field] = value.strip()
    return out


def run_import(
    csv_path: str,
    column_map: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
    batch_size: int = 100,
) -> Dict[str, int]:
    """
    Import entities from a CSV file.

    Returns a dict with keys: created, updated, skipped, errors.
    """
    mapping = column_map or DEFAULT_COLUMN_MAP
    stats = {"created": 0, "updated": 0, "skipped": 0, "errors": 0}
    error_messages: List[str] = []

    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    if dry_run:
        logger.info("[DRY RUN] Previewing import from: %s", csv_path)
    else:
        logger.info("Starting import from: %s", csv_path)

    if dry_run:
        # Just scan and count without writing
        with open(csv_path, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                mapped = _apply_mapping(row, mapping)
                if not mapped.get("entity_id"):
                    stats["skipped"] += 1
                    continue
                stats["created"] += 1  # Would be created or updated
        logger.info(
            "[DRY RUN] Would process: ~%d entities, skipped: %d",
            stats["created"],
            stats["skipped"],
        )
        return stats

    # Real import — use EntityResolutionService
    from services.entity_resolution_service import get_entity_resolution_service
    from database.connection import SessionLocal

    svc = get_entity_resolution_service()
    db = SessionLocal()

    try:
        # The service's bulk_import_from_csv handles everything
        result = svc.bulk_import_from_csv(csv_path, mapping=None, db=db)
        stats["created"] = result["created"]
        stats["updated"] = result["updated"]
        stats["skipped"] = result["skipped"]
    finally:
        db.close()

    logger.info(
        "Import complete: created=%d updated=%d skipped=%d errors=%d",
        stats["created"],
        stats["updated"],
        stats["skipped"],
        stats["errors"],
    )
    return stats


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Import entity data from SAP CSV export into FAZRI"
    )
    parser.add_argument("csv_path", help="Path to the SAP CSV export file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what would be imported without writing to the database",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of rows to commit in each database batch (default: 100)",
    )
    parser.add_argument(
        "--mapping",
        type=str,
        default=None,
        help='JSON string of {csv_column: fazri_field} overrides, e.g. \'{"empNo":"entity_id"}\'',
    )
    args = parser.parse_args()

    column_map = None
    if args.mapping:
        try:
            overrides = json.loads(args.mapping)
            column_map = {**DEFAULT_COLUMN_MAP, **overrides}
        except json.JSONDecodeError as exc:
            logger.error("Invalid --mapping JSON: %s", exc)
            sys.exit(1)

    try:
        result = run_import(
            csv_path=args.csv_path,
            column_map=column_map,
            dry_run=args.dry_run,
            batch_size=args.batch_size,
        )
    except FileNotFoundError as exc:
        logger.error(str(exc))
        sys.exit(1)
    print(json.dumps(result, indent=2))
