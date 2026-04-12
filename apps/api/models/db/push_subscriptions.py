"""
PushSubscription — stores browser Web Push subscription objects per user session.
Each row represents one browser+device that has granted notification permission.
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database.connection import Base


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Identifier from the auth session (email or entity_id)
    user_id = Column(String(255), nullable=False, index=True)
    # The push service endpoint URL (browser-specific)
    endpoint = Column(Text, nullable=False, unique=True)
    # ECDH public key (base64url)
    p256dh = Column(Text, nullable=False)
    # Authentication secret (base64url)
    auth = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    organization_id = Column(String, nullable=False, index=True, default="default-org")
