"""SQLAlchemy model for outgoing webhooks."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID

from database.connection import Base


class OutgoingWebhook(Base):
    __tablename__ = "outgoing_webhooks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    url = Column(Text, nullable=False)
    events = Column(String(500), nullable=False)  # Comma-separated event names
    secret = Column(String(100), nullable=False)
    active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    @property
    def events_list(self):
        return [e for e in self.events.split(",") if e]

    @events_list.setter
    def events_list(self, value):
        self.events = ",".join(value)
