"""
PostgreSQL-backed entity resolution service.

Replaces the CSV/pandas EntityResolver with a service that resolves
identifiers against the entity_identifiers and entity_profiles tables.

Usage
-----
    from services.entity_resolution_service import get_entity_resolution_service

    svc = get_entity_resolution_service()
    profile = svc.resolve("card_id", "C3286")
    # => EntityProfileDTO(entity_id="E100000", name="Neha Mehta", …) or None
"""

from __future__ import annotations

import csv
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Optional
from functools import lru_cache

from sqlalchemy import func, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from database.connection import SessionLocal
from models.db.entity_identifiers import EntityIdentifier
from models.db.entity_profiles import EntityProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data transfer object (lightweight, decoupled from SQLAlchemy)
# ---------------------------------------------------------------------------


@dataclass
class EntityProfileDTO:
    """Resolved entity profile — safe to pass around without a DB session."""

    entity_id: str
    name: Optional[str] = None
    role: Optional[str] = None
    email: Optional[str] = None
    department: Optional[str] = None
    authorized_zones: List[str] = field(default_factory=list)

    @classmethod
    def from_orm(cls, row: EntityProfile) -> "EntityProfileDTO":
        return cls(
            entity_id=row.entity_id,
            name=row.name,
            role=row.role,
            email=row.email,
            department=row.department,
            authorized_zones=row.authorized_zones or [],
        )


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class EntityResolutionService:
    """
    Resolves hardware identifiers to canonical FAZRI entity profiles.

    All methods accept an optional ``db`` Session parameter.  When omitted,
    a session is opened and closed automatically.  Pass an explicit session
    when you are already inside a request/transaction context.
    """

    def resolve(
        self,
        identifier_type: str,
        identifier_value: str,
        db: Optional[Session] = None,
    ) -> Optional[EntityProfileDTO]:
        """
        Direct lookup: identifier_type + identifier_value → EntityProfile.

        Returns None when the identifier is not registered.
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()
        try:
            # mac_address identifiers may be stored in mixed case (e.g. "DH6d0bd80c8f8e")
            # while sensors send lowercase — use case-insensitive comparison for MACs only.
            ident_query = db.query(EntityIdentifier).filter(
                EntityIdentifier.identifier_type == identifier_type,
                EntityIdentifier.active == True,  # noqa: E712
            )
            if identifier_type == "mac_address":
                ident_query = ident_query.filter(
                    func.lower(EntityIdentifier.identifier_value) == identifier_value.lower()
                )
            else:
                ident_query = ident_query.filter(
                    EntityIdentifier.identifier_value == str(identifier_value)
                )
            ident = ident_query.first()
            if ident is None:
                return None

            profile = (
                db.query(EntityProfile)
                .filter_by(entity_id=ident.entity_id)
                .first()
            )
            return EntityProfileDTO.from_orm(profile) if profile else None
        finally:
            if own_session:
                db.close()

    def resolve_fuzzy_name(
        self,
        name: str,
        threshold: float = 0.3,
        limit: int = 10,
        db: Optional[Session] = None,
    ) -> List[EntityProfileDTO]:
        """
        Fuzzy name search using PostgreSQL pg_trgm trigram similarity.

        Returns up to ``limit`` profiles ordered by similarity descending.
        Requires the pg_trgm extension and the GIN index on entity_profiles.name.
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()
        try:
            rows = db.execute(
                text(
                    """
                    SELECT entity_id, name, role, email, department, authorized_zones
                    FROM   entity_profiles
                    WHERE  similarity(name, :name) > :threshold
                    ORDER  BY similarity(name, :name) DESC
                    LIMIT  :limit
                    """
                ),
                {"name": name, "threshold": threshold, "limit": limit},
            ).fetchall()

            return [
                EntityProfileDTO(
                    entity_id=r.entity_id,
                    name=r.name,
                    role=r.role,
                    email=r.email,
                    department=r.department,
                    authorized_zones=r.authorized_zones or [],
                )
                for r in rows
            ]
        finally:
            if own_session:
                db.close()

    def register_identifier(
        self,
        entity_id: str,
        identifier_type: str,
        identifier_value: str,
        source: str,
        confidence: float = 1.0,
        db: Optional[Session] = None,
    ) -> None:
        """
        Upsert an identifier mapping.

        If the (identifier_type, identifier_value) pair already exists, updates
        last_seen and confidence.  Otherwise inserts a new row.
        """
        own_session = db is None
        if own_session:
            db = SessionLocal()
        try:
            now = datetime.now(timezone.utc)
            existing = (
                db.query(EntityIdentifier)
                .filter_by(
                    identifier_type=identifier_type,
                    identifier_value=str(identifier_value),
                )
                .first()
            )
            if existing:
                existing.entity_id = entity_id
                existing.confidence = confidence
                existing.last_seen = now
                existing.active = True
            else:
                db.add(
                    EntityIdentifier(
                        entity_id=entity_id,
                        identifier_type=identifier_type,
                        identifier_value=str(identifier_value),
                        source=source,
                        confidence=confidence,
                        first_seen=now,
                        last_seen=now,
                        active=True,
                    )
                )
            if own_session:
                db.commit()
        except Exception:
            if own_session:
                db.rollback()
            raise
        finally:
            if own_session:
                db.close()

    def get_entity_profile(
        self,
        entity_id: str,
        db: Optional[Session] = None,
    ) -> Optional[EntityProfileDTO]:
        """Return the profile for a known entity_id, or None."""
        own_session = db is None
        if own_session:
            db = SessionLocal()
        try:
            profile = (
                db.query(EntityProfile).filter_by(entity_id=entity_id).first()
            )
            return EntityProfileDTO.from_orm(profile) if profile else None
        finally:
            if own_session:
                db.close()

    def get_authorized_zones(
        self,
        entity_id: str,
        db: Optional[Session] = None,
    ) -> List[str]:
        """Return the list of authorized zone_ids for an entity."""
        profile = self.get_entity_profile(entity_id, db=db)
        return profile.authorized_zones if profile else []

    def bulk_import_from_csv(
        self,
        csv_path: str,
        mapping: Optional[dict] = None,
        db: Optional[Session] = None,
    ) -> dict:
        """
        Read a CSV and upsert entity_profiles + entity_identifiers.

        Default expected columns (override via ``mapping``):
            entity_id, name, role, email, department,
            student_id, staff_id, card_id, device_hash, face_id

        Returns a dict with keys: created, updated, skipped.
        """
        # Column → identifier_type mapping
        identifier_columns = {
            "student_id": "student_id",
            "staff_id": "staff_id",
            "card_id": "card_id",
            "device_hash": "mac_address",
            "face_id": "face_id",
            "email": "email",
        }

        own_session = db is None
        if own_session:
            db = SessionLocal()

        stats = {"created": 0, "updated": 0, "skipped": 0}
        try:
            with open(csv_path, newline="", encoding="utf-8") as fh:
                reader = csv.DictReader(fh)
                for row in reader:
                    entity_id = (row.get("entity_id") or "").strip()
                    if not entity_id:
                        stats["skipped"] += 1
                        continue

                    # Upsert entity_profile
                    existing = (
                        db.query(EntityProfile)
                        .filter_by(entity_id=entity_id)
                        .first()
                    )
                    if existing:
                        existing.name = row.get("name") or existing.name
                        existing.role = row.get("role") or existing.role
                        existing.email = row.get("email") or existing.email
                        existing.department = (
                            row.get("department") or existing.department
                        )
                        stats["updated"] += 1
                    else:
                        db.add(
                            EntityProfile(
                                entity_id=entity_id,
                                name=row.get("name"),
                                role=row.get("role"),
                                email=row.get("email"),
                                department=row.get("department"),
                                authorized_zones=[],
                            )
                        )
                        stats["created"] += 1

                    # Upsert each non-empty identifier using INSERT … ON CONFLICT
                    # to avoid duplicate-key errors when the same identifier
                    # value appears multiple times within one batch.
                    now = datetime.now(timezone.utc)
                    for col, id_type in identifier_columns.items():
                        value = (row.get(col) or "").strip()
                        if not value:
                            continue
                        stmt = (
                            pg_insert(EntityIdentifier)
                            .values(
                                entity_id=entity_id,
                                identifier_type=id_type,
                                identifier_value=value,
                                source="sap_import",
                                confidence=1.0,
                                first_seen=now,
                                last_seen=now,
                                active=True,
                            )
                            .on_conflict_do_update(
                                constraint="uq_entity_identifiers_type_value",
                                set_={
                                    "entity_id": entity_id,
                                    "last_seen": now,
                                    "active": True,
                                },
                            )
                        )
                        db.execute(stmt)

                    # Commit in batches of 500 to avoid one giant transaction
                    if (stats["created"] + stats["updated"]) % 500 == 0:
                        db.commit()

            db.commit()
            logger.info(
                "CSV import complete: created=%d updated=%d skipped=%d",
                stats["created"],
                stats["updated"],
                stats["skipped"],
            )
        except Exception:
            db.rollback()
            raise
        finally:
            if own_session:
                db.close()

        return stats


# ---------------------------------------------------------------------------
# Singleton factory
# ---------------------------------------------------------------------------

_service: Optional[EntityResolutionService] = None


def get_entity_resolution_service() -> EntityResolutionService:
    """Return the process-level EntityResolutionService singleton."""
    global _service
    if _service is None:
        _service = EntityResolutionService()
    return _service
