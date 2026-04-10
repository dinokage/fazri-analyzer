# Models package
# This package contains both Pydantic models (for API validation) and SQLAlchemy models (for database)

# Pydantic models for entity resolution
from .entity import (
    Identifier,
    Entity,
    ActivityEvent,
    Timeline,
)

# Pydantic models for chat
from .chat import (
    MessageRole,
    ChatMessage,
    ChatRequest,
    ToolCall,
    ChatResponse,
    ConversationState,
    ErrorResponse,
)

# SQLAlchemy database models
from .db import (
    # Alert models
    Alert,
    AlertAssignment,
    AlertAuditLog,
    StaffProfile,
    StaffLocation,
    NotificationQueue,
    NotificationLog,
    DemoScenario,
    DemoTimelineEvent,
    # Enums
    AlertStatus,
    AlertSeverity,
    StaffRole,
    AuditAction,
    NotificationChannel,
    NotificationStatus,
)

# Pydantic schemas for API
from .schemas import (
    # Alert schemas
    AlertBase,
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse,
    AlertStatusUpdate,
    AlertResolve,
    # Staff schemas
    StaffProfileBase,
    StaffProfileCreate,
    StaffProfileUpdate,
    StaffProfileResponse,
    StaffLocationUpdate,
    StaffLocationResponse,
    StaffNearbyRequest,
    StaffNearbyResponse,
    # Assignment schemas
    AlertAssignmentCreate,
    AlertAssignmentResponse,
    # Audit schemas
    AuditLogResponse,
    AuditLogListResponse,
    # Notification schemas
    NotificationCreate,
    NotificationResponse,
    # Demo schemas
    DemoScenarioResponse,
    DemoStartRequest,
    DemoStateResponse,
    DemoControlRequest,
    # Common schemas
    LocationSchema,
    PaginationParams,
    PaginatedResponse,
)

__all__ = [
    # Entity models
    "Identifier",
    "Entity",
    "ActivityEvent",
    "Timeline",
    # Chat models
    "MessageRole",
    "ChatMessage",
    "ChatRequest",
    "ToolCall",
    "ChatResponse",
    "ConversationState",
    "ErrorResponse",
    # Database models
    "Alert",
    "AlertAssignment",
    "AlertAuditLog",
    "StaffProfile",
    "StaffLocation",
    "NotificationQueue",
    "NotificationLog",
    "DemoScenario",
    "DemoTimelineEvent",
    # Database enums
    "AlertStatus",
    "AlertSeverity",
    "StaffRole",
    "AuditAction",
    "NotificationChannel",
    "NotificationStatus",
    # API schemas
    "AlertBase",
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "AlertListResponse",
    "AlertStatusUpdate",
    "AlertResolve",
    "StaffProfileBase",
    "StaffProfileCreate",
    "StaffProfileUpdate",
    "StaffProfileResponse",
    "StaffLocationUpdate",
    "StaffLocationResponse",
    "StaffNearbyRequest",
    "StaffNearbyResponse",
    "AlertAssignmentCreate",
    "AlertAssignmentResponse",
    "AuditLogResponse",
    "AuditLogListResponse",
    "NotificationCreate",
    "NotificationResponse",
    "DemoScenarioResponse",
    "DemoStartRequest",
    "DemoStateResponse",
    "DemoControlRequest",
    "LocationSchema",
    "PaginationParams",
    "PaginatedResponse",
]
