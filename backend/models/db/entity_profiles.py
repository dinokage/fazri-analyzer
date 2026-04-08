"""
SQLAlchemy model for entity profiles.

One row per known entity (student, staff, faculty, visitor).
entity_id is the primary key and the canonical cross-table reference.
"""

import sqlalchemy as sa
from sqlalchemy import Column, DateTime, JSON, String

from database.connection import Base


class EntityProfile(Base):
    """
    Canonical FAZRI entity profile.

    authorized_zones is a JSON list of zone_ids this entity may access.
    An empty list means no zone restrictions are configured (fully authorized).
    """

    __tablename__ = "entity_profiles"

    entity_id = Column(String, primary_key=True, nullable=False)

    name = Column(String, nullable=True)

    # STUDENT | STAFF | FACULTY | VISITOR | UNKNOWN
    role = Column(String, nullable=True)

    email = Column(String, nullable=True, index=True)
    department = Column(String, nullable=True)

    # JSON list of zone_ids, e.g. ["LIB_ENT", "CAF_01", "LAB_101"]
    authorized_zones = Column(JSON, nullable=False, default=list)

    # Connector-specific extension fields
    metadata_ = Column("metadata", JSON, nullable=False, default=dict)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
        onupdate=sa.text("now()"),
    )

    def __repr__(self) -> str:
        return f"<EntityProfile {self.entity_id} name={self.name} role={self.role}>"
