"""
SQLAlchemy model for entity identifier mappings.

Each row maps a hardware-level or system identifier (card_id, mac_address,
face_id, student_id, …) to a canonical FAZRI entity_id.  A single entity
will have multiple rows — one per identifier type.
"""

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID

from database.connection import Base


class EntityIdentifier(Base):
    """
    Maps an identifier (card number, MAC, face label, …) to a FAZRI entity_id.

    The (identifier_type, identifier_value) pair is unique — only one entity
    may own a given card or MAC at any point in time.
    """

    __tablename__ = "entity_identifiers"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("uuid_generate_v4()"),
        nullable=False,
    )

    # The canonical FAZRI entity this identifier belongs to
    entity_id = Column(String, index=True, nullable=False)

    # e.g. "card_id", "mac_address", "face_id", "student_id", "staff_id", "email"
    identifier_type = Column(String, index=True, nullable=False)
    identifier_value = Column(String, index=True, nullable=False)

    # Where this mapping came from: "sap_import", "manual", "wifi_learning"
    source = Column(String, nullable=False, default="manual")

    # 1.0 for deterministic sources (RFID card), <1.0 for learned mappings
    confidence = Column(Float, nullable=False, default=1.0)

    first_seen = Column(DateTime(timezone=True), nullable=False,
                        server_default=sa.text("now()"))
    last_seen = Column(DateTime(timezone=True), nullable=False,
                       server_default=sa.text("now()"),
                       onupdate=sa.text("now()"))

    active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), nullable=False,
                        server_default=sa.text("now()"))

    __table_args__ = (
        UniqueConstraint(
            "identifier_type",
            "identifier_value",
            name="uq_entity_identifiers_type_value",
        ),
        # ix_entity_identifiers_type_value omitted: the UNIQUE constraint above
        # already creates a B-tree index on (identifier_type, identifier_value).
    )

    def __repr__(self) -> str:
        return (
            f"<EntityIdentifier {self.identifier_type}={self.identifier_value} "
            f"→ {self.entity_id}>"
        )
