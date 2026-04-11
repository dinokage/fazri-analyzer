"""
Pydantic schemas for the Alert System.
Used for request/response validation in API endpoints.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from enum import Enum


# ============================================================================
# ENUMS (mirroring SQLAlchemy enums for API use)
# ============================================================================

class AlertStatusEnum(str, Enum):
    """Alert lifecycle status"""
    CREATED = "created"
    ASSIGNED = "assigned"
    ACKNOWLEDGED = "acknowledged"
    INVESTIGATING = "investigating"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class AlertSeverityEnum(str, Enum):
    """Alert severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ResolutionTypeEnum(str, Enum):
    """Resolution outcome types"""
    FALSE_ALARM = "false_alarm"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    NO_ACTION_REQUIRED = "no_action_required"


class StaffRoleEnum(str, Enum):
    """Staff role types"""
    SECURITY = "security"
    SUPERVISOR = "supervisor"
    ADMIN = "admin"
    LAB_SUPERVISOR = "lab_supervisor"


class AuditActionEnum(str, Enum):
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


class ActorTypeEnum(str, Enum):
    """Actor types for audit logging"""
    ADMIN = "admin"
    STAFF = "staff"
    SYSTEM = "system"


class NotificationChannelEnum(str, Enum):
    """Notification delivery channels"""
    WEBSOCKET = "websocket"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


# ============================================================================
# COMMON SCHEMAS
# ============================================================================

class LocationSchema(BaseModel):
    """Location information for alerts"""
    zone_id: str = Field(..., description="Zone identifier (e.g., 'LAB_101')")
    building: Optional[str] = Field(None, description="Building name")
    floor: Optional[str] = Field(None, description="Floor number/name")
    coordinates: Optional[Dict[str, float]] = Field(None, description="GPS coordinates {lat, lng}")

    model_config = ConfigDict(from_attributes=True)


class PaginationParams(BaseModel):
    """Pagination parameters"""
    offset: int = Field(0, ge=0, description="Number of items to skip")
    limit: int = Field(20, ge=1, le=100, description="Maximum number of items to return")


class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper"""
    total: int = Field(..., description="Total number of items")
    offset: int = Field(..., description="Current offset")
    limit: int = Field(..., description="Items per page")
    has_more: bool = Field(..., description="Whether more items exist")


# ============================================================================
# STAFF SCHEMAS
# ============================================================================

class ContactPreferencesSchema(BaseModel):
    """Staff contact preferences"""
    email: bool = True
    sms: bool = False
    push: bool = True


class StaffProfileBase(BaseModel):
    """Base schema for staff profiles"""
    name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=50)
    role: StaffRoleEnum = StaffRoleEnum.SECURITY
    department: Optional[str] = Field(None, max_length=100)
    on_duty: bool = False
    max_concurrent_assignments: int = Field(3, ge=1, le=10)
    contact_preferences: ContactPreferencesSchema = Field(default_factory=ContactPreferencesSchema)


class StaffProfileCreate(StaffProfileBase):
    """Schema for creating a new staff profile"""
    entity_id: Optional[str] = Field(None, description="Link to campus entity")
    is_mock_user: bool = False


class StaffProfileUpdate(BaseModel):
    """Schema for updating a staff profile"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=50)
    role: Optional[StaffRoleEnum] = None
    department: Optional[str] = Field(None, max_length=100)
    on_duty: Optional[bool] = None
    max_concurrent_assignments: Optional[int] = Field(None, ge=1, le=10)
    contact_preferences: Optional[ContactPreferencesSchema] = None


class StaffProfileResponse(StaffProfileBase):
    """Schema for staff profile response"""
    id: UUID
    entity_id: Optional[str] = None
    is_mock_user: bool
    created_at: datetime
    updated_at: datetime
    current_assignment_count: int = Field(0, description="Number of active assignments")

    model_config = ConfigDict(from_attributes=True)


class StaffLocationUpdate(BaseModel):
    """Schema for updating staff location"""
    zone_id: str = Field(..., max_length=50)
    building: Optional[str] = Field(None, max_length=100)
    floor: Optional[str] = Field(None, max_length=20)
    source: str = Field("manual", description="Source of location update")


class StaffLocationResponse(BaseModel):
    """Schema for staff location response"""
    id: UUID
    staff_id: UUID
    zone_id: str
    building: Optional[str]
    floor: Optional[str]
    source: str
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class StaffNearbyRequest(BaseModel):
    """Request schema for finding nearby staff"""
    zone_id: str = Field(..., description="Zone to search near")
    max_distance_zones: int = Field(3, ge=1, le=10, description="Maximum zone distance")
    include_off_duty: bool = Field(False, description="Include off-duty staff")
    exclude_staff_ids: List[UUID] = Field(default_factory=list, description="Staff IDs to exclude")


class StaffNearbyResponse(BaseModel):
    """Response schema for nearby staff"""
    staff: StaffProfileResponse
    zone_id: str
    distance_zones: int = Field(..., description="Number of zones away")
    last_seen: datetime


# ============================================================================
# ALERT SCHEMAS
# ============================================================================

class AlertBase(BaseModel):
    """Base schema for alerts"""
    title: str = Field(..., min_length=1, max_length=500)
    description: str = Field(..., min_length=1)
    severity: AlertSeverityEnum = AlertSeverityEnum.MEDIUM
    location: LocationSchema
    anomaly_type: Optional[str] = Field(None, max_length=50)
    affected_entities: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)


class AlertCreate(AlertBase):
    """Schema for creating a new alert"""
    anomaly_id: Optional[str] = Field(None, description="Reference to anomaly detection")
    is_mock: bool = False
    mock_scenario: Optional[str] = None


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = Field(None, min_length=1)
    severity: Optional[AlertSeverityEnum] = None
    location: Optional[LocationSchema] = None
    evidence: Optional[Dict[str, Any]] = None


class AlertStatusUpdate(BaseModel):
    """Schema for updating alert status"""
    status: AlertStatusEnum
    notes: Optional[str] = Field(None, description="Optional notes for status change")


class AlertResolve(BaseModel):
    """Schema for resolving an alert"""
    resolution_type: ResolutionTypeEnum
    resolution_notes: str = Field(..., min_length=1, description="Required resolution notes")
    action_taken: Optional[str] = Field(None, description="Description of action taken")


class AlertResponse(AlertBase):
    """Schema for alert response"""
    id: UUID
    anomaly_id: Optional[str]
    status: AlertStatusEnum
    assigned_to: Optional[UUID]
    assigned_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    resolved_by: Optional[UUID]
    resolution_type: Optional[ResolutionTypeEnum]
    resolution_notes: Optional[str]
    escalation_count: int
    is_mock: bool
    mock_scenario: Optional[str]
    created_at: datetime
    updated_at: datetime

    # Nested info (optional, populated based on include params)
    assigned_staff_name: Optional[str] = None
    resolver_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AlertListResponse(PaginatedResponse):
    """Paginated alert list response"""
    alerts: List[AlertResponse]


# ============================================================================
# ASSIGNMENT SCHEMAS
# ============================================================================

class AlertAssignmentCreate(BaseModel):
    """Schema for creating an alert assignment"""
    staff_id: UUID
    assignment_reason: str = Field("manual", description="Reason for assignment")


class AlertAssignmentResponse(BaseModel):
    """Schema for assignment response"""
    id: UUID
    alert_id: UUID
    staff_id: UUID
    staff_name: str
    assigned_at: datetime
    acknowledged_at: Optional[datetime]
    completed_at: Optional[datetime]
    assignment_reason: Optional[str]
    proximity_score: Optional[float]
    is_active: bool

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# AUDIT LOG SCHEMAS
# ============================================================================

class AuditLogResponse(BaseModel):
    """Schema for audit log entry response"""
    id: UUID
    alert_id: UUID
    action: AuditActionEnum
    actor_id: Optional[UUID]
    actor_type: ActorTypeEnum
    actor_name: Optional[str] = None
    details: Dict[str, Any]
    ip_address: Optional[str]
    is_mock: bool
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(PaginatedResponse):
    """Paginated audit log response"""
    logs: List[AuditLogResponse]


# ============================================================================
# NOTIFICATION SCHEMAS
# ============================================================================

class NotificationCreate(BaseModel):
    """Schema for creating a notification"""
    alert_id: UUID
    recipient_id: UUID
    channel: NotificationChannelEnum
    title: str = Field(..., max_length=255)
    body: str
    action_url: Optional[str] = Field(None, max_length=500)
    data: Dict[str, Any] = Field(default_factory=dict)
    is_mock: bool = False


class NotificationResponse(BaseModel):
    """Schema for notification response"""
    id: UUID
    alert_id: UUID
    recipient_id: UUID
    channel: NotificationChannelEnum
    priority: AlertSeverityEnum
    title: str
    body: str
    status: str
    retry_count: int
    created_at: datetime
    processed_at: Optional[datetime]

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# DEMO SYSTEM SCHEMAS
# ============================================================================

class DemoTimelineEventResponse(BaseModel):
    """Schema for demo timeline event"""
    id: UUID
    step_number: int
    delay_seconds: int
    action: str
    description: str
    action_data: Dict[str, Any]
    narration_text: Optional[str]

    model_config = ConfigDict(from_attributes=True)


class DemoScenarioResponse(BaseModel):
    """Schema for demo scenario response"""
    id: str
    name: str
    description: str
    severity: AlertSeverityEnum
    duration_seconds: int
    auto_advance: bool
    default_speed: float
    display_order: int
    is_active: bool
    timeline_events: List[DemoTimelineEventResponse] = []

    model_config = ConfigDict(from_attributes=True)


class DemoStartRequest(BaseModel):
    """Schema for starting a demo scenario"""
    scenario_id: str
    speed: float = Field(1.0, ge=0.1, le=10.0, description="Playback speed multiplier")
    auto_advance: bool = Field(True, description="Auto-advance through timeline")


class DemoStateResponse(BaseModel):
    """Schema for current demo state"""
    is_active: bool
    scenario_id: Optional[str]
    scenario_name: Optional[str]
    alert_id: Optional[UUID]
    current_step: int
    total_steps: int
    current_status: Optional[AlertStatusEnum]
    elapsed_seconds: float
    speed: float
    auto_advance: bool
    next_step_description: Optional[str]
    next_step_in_seconds: Optional[float]


class DemoControlRequest(BaseModel):
    """Schema for demo control actions"""
    action: str = Field(..., description="Control action: 'advance', 'pause', 'resume', 'reset', 'set_speed'")
    speed: Optional[float] = Field(None, ge=0.1, le=10.0, description="Speed for 'set_speed' action")


# ============================================================================
# WEBSOCKET EVENT SCHEMAS
# ============================================================================

class WebSocketAlertEvent(BaseModel):
    """Schema for WebSocket alert events"""
    event_type: str = Field(..., description="Event type: alert.created, alert.updated, etc.")
    alert: AlertResponse
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class WebSocketDemoEvent(BaseModel):
    """Schema for WebSocket demo events"""
    event_type: str = Field(..., description="Event type: demo.started, demo.step_advanced, etc.")
    state: DemoStateResponse
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ============================================================================
# NOTIFICATION SCHEMAS
# ============================================================================

class NotificationStatusEnum(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"


class NotificationQueueResponse(BaseModel):
    """Schema for notification queue entries"""
    id: UUID
    staff_id: UUID
    alert_id: UUID
    channel: NotificationChannelEnum
    subject: str
    message: str
    priority: str
    status: NotificationStatusEnum
    retry_count: int
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class NotificationLogResponse(BaseModel):
    """Schema for notification delivery logs"""
    id: UUID
    notification_id: Optional[UUID] = None
    staff_id: UUID
    alert_id: UUID
    channel: NotificationChannelEnum
    recipient: str
    subject: str
    status: NotificationStatusEnum
    sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class NotificationHistoryResponse(BaseModel):
    """Paginated notification history response"""
    total: int
    logs: List[NotificationLogResponse]


class NotificationQueueStatusResponse(BaseModel):
    """Status summary of the notification queue"""
    pending: int
    failed: int
    sent_today: int
    providers_enabled: List[str]


class ProcessQueueResponse(BaseModel):
    """Response from processing notification queue"""
    message: str
    results: Dict[str, int]
