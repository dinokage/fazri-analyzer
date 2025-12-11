"""
SQLAlchemy models for the Alert System.
Includes all database tables for alerts, staff management, audit logging, and demo system.
"""

import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    String,
    Text,
    DateTime,
    Boolean,
    Integer,
    Float,
    JSON,
    ForeignKey,
    Enum,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid

from database.connection import Base


# ============================================================================
# ENUMS
# ============================================================================

class AlertStatus(str, enum.Enum):
    """Alert lifecycle status"""
    CREATED = "created"
    ASSIGNED = "assigned"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class AlertSeverity(str, enum.Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionType(str, enum.Enum):
    """Resolution outcome types"""
    FALSE_ALARM = "false_alarm"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    NO_ACTION_REQUIRED = "no_action_required"


class StaffRole(str, enum.Enum):
    """Staff role types"""
    SECURITY = "security"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    LAB_SUPERVISOR = "lab_supervisor"


class AuditAction(str, enum.Enum):
    """Audit log action types"""
    CREATED = "created"
    ASSIGNED = "assigned"
    ACKNOWLEDGED = "acknowledged"
    STATUS_CHANGED = "status_changed"
    NOTE_ADDED = "note_added"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    REASSIGNED = "reassigned"
    SEVERITY_CHANGED = "severity_changed"
    BACKUP_REQUESTED = "backup_requested"


class ActorType(str, enum.Enum):
    """Actor types for audit logging"""
    ADMIN = "admin"
    STAFF = "staff"
    SYSTEM = "system"


class NotificationChannel(str, enum.Enum):
    """Notification delivery channels"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, enum.Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"


# ============================================================================
# STAFF MODELS
# ============================================================================

class StaffProfile(Base):
    """Security staff profile for alert assignments"""
    __tablename__ = "staff_profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_id = Column(String(100), unique=True, nullable=True, index=True)  # Links to campus entity
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(50), nullable=True)
    role = Column(Enum(StaffRole), nullable=False, default=StaffRole.SECURITY)
    department = Column(String(100), nullable=True)

    # Availability
    on_duty = Column(Boolean, default=False)
    max_concurrent_assignments = Column(Integer, default=3)

    # Contact preferences (JSON: {email: bool, sms: bool, push: bool})
    contact_preferences = Column(JSON, default=lambda: {"email": True, "sms": False, "push": True})

    # Demo flag
    is_mock_user = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    locations = relationship("StaffLocation", back_populates="staff", cascade="all, delete-orphan")
    assignments = relationship("AlertAssignment", back_populates="staff")
    audit_logs = relationship("AlertAuditLog", back_populates="actor_staff", foreign_keys="AlertAuditLog.actor_id")

    # Indexes
    __table_args__ = (
        Index("ix_staff_profiles_on_duty", "on_duty"),
        Index("ix_staff_profiles_role", "role"),
    )

    def __repr__(self):
        return f"<StaffProfile(id={self.id}, name={self.name}, role={self.role})>"


class StaffLocation(Base):
    """Real-time staff location tracking"""
    __tablename__ = "staff_locations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id", ondelete="CASCADE"), nullable=False)
    zone_id = Column(String(50), nullable=False, index=True)

    # Location details
    building = Column(String(100), nullable=True)
    floor = Column(String(20), nullable=True)

    # Source of location data
    source = Column(String(50), default="card_swipe")  # card_swipe, manual, gps

    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    staff = relationship("StaffProfile", back_populates="locations")

    __table_args__ = (
        Index("ix_staff_locations_staff_timestamp", "staff_id", "timestamp"),
    )

    def __repr__(self):
        return f"<StaffLocation(staff_id={self.staff_id}, zone={self.zone_id})>"


# ============================================================================
# ALERT MODELS
# ============================================================================

class Alert(Base):
    """Main alert table for anomaly alerts"""
    __tablename__ = "alerts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Reference to anomaly detection
    anomaly_id = Column(String(100), nullable=True, index=True)  # Links to anomalies table
    anomaly_type = Column(String(50), nullable=True)  # Type of anomaly detected

    # Alert metadata
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False, default=AlertSeverity.MEDIUM)
    status = Column(Enum(AlertStatus), nullable=False, default=AlertStatus.CREATED)

    # Location information (JSON)
    location = Column(JSON, nullable=False)
    # Expected structure:
    # {
    #     "zone_id": "LAB_101",
    #     "building": "Science Building A",
    #     "floor": "3",
    #     "coordinates": {"lat": 40.7128, "lng": -74.0060}
    # }

    # Affected entities (JSON array of entity IDs)
    affected_entities = Column(JSON, default=list)

    # Data sources that detected this anomaly (JSON array)
    data_sources = Column(JSON, default=list)  # ["CARD_SWIPE", "WIFI", "CCTV"]

    # Evidence and details (JSON)
    evidence = Column(JSON, default=dict)

    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    # Acknowledgment
    acknowledged_at = Column(DateTime, nullable=True)

    # Resolution
    resolved_at = Column(DateTime, nullable=True)
    resolved_by = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=True)
    resolution_type = Column(Enum(ResolutionType), nullable=True)
    resolution_notes = Column(Text, nullable=True)

    # Escalation tracking
    escalation_count = Column(Integer, default=0)
    escalation_history = Column(JSON, default=list)

    # Demo/Mock flag
    is_mock = Column(Boolean, default=False, index=True)
    mock_scenario = Column(String(100), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    assigned_staff = relationship("StaffProfile", foreign_keys=[assigned_to], backref="alerts_assigned")
    resolver = relationship("StaffProfile", foreign_keys=[resolved_by], backref="alerts_resolved")
    assignments = relationship("AlertAssignment", back_populates="alert", cascade="all, delete-orphan")
    audit_logs = relationship("AlertAuditLog", back_populates="alert", cascade="all, delete-orphan")
    notifications = relationship("NotificationQueue", back_populates="alert", cascade="all, delete-orphan")

    # Indexes
    __table_args__ = (
        Index("ix_alerts_status_severity", "status", "severity"),
        Index("ix_alerts_created_at_desc", "created_at"),
        Index("ix_alerts_assigned_to_status", "assigned_to", "status"),
        CheckConstraint(
            "escalation_count >= 0",
            name="check_escalation_count_positive"
        ),
    )

    def __repr__(self):
        return f"<Alert(id={self.id}, title={self.title[:30]}, status={self.status})>"


class AlertAssignment(Base):
    """Assignment history for alerts"""
    __tablename__ = "alert_assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    staff_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=False)

    # Assignment details
    assigned_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Assignment metadata
    assignment_reason = Column(String(255), nullable=True)  # "proximity", "manual", "escalation"
    proximity_score = Column(Float, nullable=True)  # Distance-based score used for assignment

    # Was this assignment active or reassigned
    is_active = Column(Boolean, default=True)

    # Relationships
    alert = relationship("Alert", back_populates="assignments")
    staff = relationship("StaffProfile", back_populates="assignments")

    __table_args__ = (
        Index("ix_alert_assignments_alert_active", "alert_id", "is_active"),
        Index("ix_alert_assignments_staff_active", "staff_id", "is_active"),
    )

    def __repr__(self):
        return f"<AlertAssignment(alert={self.alert_id}, staff={self.staff_id})>"


# ============================================================================
# AUDIT LOG
# ============================================================================

class AlertAuditLog(Base):
    """Immutable audit log for all alert actions"""
    __tablename__ = "alert_audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)

    # Action details
    action = Column(Enum(AuditAction), nullable=False)
    actor_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=True)  # NULL for system actions
    actor_type = Column(Enum(ActorType), nullable=False, default=ActorType.SYSTEM)

    # Change details (JSON)
    details = Column(JSON, default=dict)
    # Expected structure:
    # {
    #     "previous_state": {...},
    #     "new_state": {...},
    #     "reason": "string"
    # }

    # Request metadata
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(500), nullable=True)

    # Demo flag
    is_mock = Column(Boolean, default=False)

    # Timestamp (immutable)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    alert = relationship("Alert", back_populates="audit_logs")
    actor_staff = relationship("StaffProfile", back_populates="audit_logs", foreign_keys=[actor_id])

    __table_args__ = (
        Index("ix_audit_logs_alert_timestamp", "alert_id", "timestamp"),
        Index("ix_audit_logs_actor_timestamp", "actor_id", "timestamp"),
        Index("ix_audit_logs_action", "action"),
    )

    def __repr__(self):
        return f"<AlertAuditLog(alert={self.alert_id}, action={self.action})>"


# ============================================================================
# NOTIFICATION MODELS
# ============================================================================

class NotificationQueue(Base):
    """Queue for pending notifications"""
    __tablename__ = "notification_queue"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    alert_id = Column(UUID(as_uuid=True), ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=False)

    # Notification details
    channel = Column(Enum(NotificationChannel), nullable=False)
    priority = Column(Enum(AlertSeverity), nullable=False)  # Uses same enum as alert severity

    # Content
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    action_url = Column(String(500), nullable=True)
    data = Column(JSON, default=dict)  # Additional payload

    # Status tracking
    status = Column(Enum(NotificationStatus), default=NotificationStatus.PENDING)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)

    # Demo flag
    is_mock = Column(Boolean, default=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    scheduled_at = Column(DateTime, default=datetime.utcnow)  # For delayed notifications
    processed_at = Column(DateTime, nullable=True)

    # Relationships
    alert = relationship("Alert", back_populates="notifications")
    recipient = relationship("StaffProfile", backref="notifications_received")

    __table_args__ = (
        Index("ix_notification_queue_status_scheduled", "status", "scheduled_at"),
        Index("ix_notification_queue_recipient_status", "recipient_id", "status"),
    )

    def __repr__(self):
        return f"<NotificationQueue(id={self.id}, channel={self.channel}, status={self.status})>"


class NotificationLog(Base):
    """Log of all notification delivery attempts"""
    __tablename__ = "notification_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    notification_id = Column(UUID(as_uuid=True), ForeignKey("notification_queue.id", ondelete="SET NULL"), nullable=True)

    # Delivery details
    channel = Column(Enum(NotificationChannel), nullable=False)
    recipient_id = Column(UUID(as_uuid=True), ForeignKey("staff_profiles.id"), nullable=False)
    recipient_address = Column(String(255), nullable=True)  # email, phone, etc.

    # Status
    status = Column(Enum(NotificationStatus), nullable=False)
    error_message = Column(Text, nullable=True)

    # External service response
    external_id = Column(String(255), nullable=True)  # ID from SendGrid, Twilio, etc.
    response_data = Column(JSON, nullable=True)

    # Timestamps
    sent_at = Column(DateTime, default=datetime.utcnow)
    delivered_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)

    # Relationships
    notification = relationship("NotificationQueue", backref="delivery_logs")
    recipient = relationship("StaffProfile", backref="notification_logs")

    __table_args__ = (
        Index("ix_notification_logs_notification_id", "notification_id"),
        Index("ix_notification_logs_sent_at", "sent_at"),
    )

    def __repr__(self):
        return f"<NotificationLog(id={self.id}, status={self.status})>"


# ============================================================================
# DEMO SYSTEM MODELS
# ============================================================================

class DemoScenario(Base):
    """Pre-defined demo scenarios"""
    __tablename__ = "demo_scenarios"

    id = Column(String(100), primary_key=True)  # e.g., "unauthorized_access"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(Enum(AlertSeverity), nullable=False)
    duration_seconds = Column(Integer, nullable=False)  # Expected duration

    # Alert template (JSON)
    alert_template = Column(JSON, nullable=False)
    # Expected structure matches Alert fields:
    # {
    #     "title": "...",
    #     "description": "...",
    #     "location": {...},
    #     "affected_entities": [...],
    #     "data_sources": [...],
    #     "evidence": {...}
    # }

    # Configuration
    auto_advance = Column(Boolean, default=True)
    default_speed = Column(Float, default=1.0)

    # Ordering for UI
    display_order = Column(Integer, default=0)

    # Active/inactive
    is_active = Column(Boolean, default=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    timeline_events = relationship("DemoTimelineEvent", back_populates="scenario", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<DemoScenario(id={self.id}, name={self.name})>"


class DemoTimelineEvent(Base):
    """Timeline events/steps for demo scenarios"""
    __tablename__ = "demo_timeline_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    scenario_id = Column(String(100), ForeignKey("demo_scenarios.id", ondelete="CASCADE"), nullable=False)

    # Event details
    step_number = Column(Integer, nullable=False)
    delay_seconds = Column(Integer, nullable=False)  # Seconds after scenario start

    # What happens at this step
    action = Column(String(100), nullable=False)  # e.g., "assign", "acknowledge", "resolve"
    description = Column(String(500), nullable=False)  # Human-readable description

    # Data for this step (JSON)
    action_data = Column(JSON, default=dict)
    # Varies by action type:
    # assign: {"staff_name": "Officer Johnson", "staff_role": "security"}
    # acknowledge: {}
    # resolve: {"resolution_type": "false_alarm", "notes": "..."}

    # UI hints
    narration_text = Column(Text, nullable=True)  # For presentation mode

    # Relationships
    scenario = relationship("DemoScenario", back_populates="timeline_events")

    __table_args__ = (
        Index("ix_demo_timeline_scenario_step", "scenario_id", "step_number"),
    )

    def __repr__(self):
        return f"<DemoTimelineEvent(scenario={self.scenario_id}, step={self.step_number})>"
