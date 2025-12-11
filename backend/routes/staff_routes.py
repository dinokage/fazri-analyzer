"""
Staff API Routes
Provides REST endpoints for staff profile and location management.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from services.alerts import StaffService, AlertService, NotificationService, AssignmentEngine
from models.db.alerts import AlertStatus, ActorType
from models.schemas.alerts import (
    StaffProfileCreate,
    StaffProfileUpdate,
    StaffProfileResponse,
    StaffLocationUpdate,
    StaffLocationResponse,
    StaffRoleEnum,
    ContactPreferencesSchema,
    AlertResponse,
    AlertStatusEnum,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/staff", tags=["staff"])


def staff_to_response(staff, db: Session) -> StaffProfileResponse:
    """Convert StaffProfile model to StaffProfileResponse schema"""
    service = StaffService(db)
    active_count = service.get_active_assignment_count(staff.id)

    return StaffProfileResponse(
        id=staff.id,
        entity_id=staff.entity_id,
        name=staff.name,
        email=staff.email,
        phone=staff.phone,
        role=StaffRoleEnum(staff.role.value),
        department=staff.department,
        on_duty=staff.on_duty,
        max_concurrent_assignments=staff.max_concurrent_assignments,
        contact_preferences=ContactPreferencesSchema(**staff.contact_preferences),
        is_mock_user=staff.is_mock_user,
        created_at=staff.created_at,
        updated_at=staff.updated_at,
        current_assignment_count=active_count,
    )


# =============================================================================
# STAFF PROFILE CRUD
# =============================================================================

@router.post("", response_model=StaffProfileResponse, status_code=201)
async def create_staff(
    staff_data: StaffProfileCreate,
    db: Session = Depends(get_db),
):
    """Create a new staff profile"""
    service = StaffService(db)

    # Check for duplicate email
    existing = service.get_staff_by_email(staff_data.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    staff = service.create_staff(staff_data)
    return staff_to_response(staff, db)


@router.get("", response_model=List[StaffProfileResponse])
async def list_staff(
    role: Optional[StaffRoleEnum] = Query(None, description="Filter by role"),
    on_duty: Optional[bool] = Query(None, description="Filter by on-duty status"),
    is_mock: Optional[bool] = Query(None, description="Filter by mock flag"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    db: Session = Depends(get_db),
):
    """List all staff with optional filters"""
    service = StaffService(db)
    staff_list, total = service.get_all_staff(
        role=role,
        on_duty=on_duty,
        is_mock=is_mock,
        limit=limit,
        offset=offset,
    )

    return [staff_to_response(s, db) for s in staff_list]


@router.get("/available", response_model=List[StaffProfileResponse])
async def list_available_staff(
    role: Optional[StaffRoleEnum] = Query(None, description="Filter by role"),
    db: Session = Depends(get_db),
):
    """
    List all staff available for new assignments.

    Returns staff who are:
    - On duty
    - Have not reached their max concurrent assignments
    """
    service = StaffService(db)
    staff_list = service.get_available_staff(role=role)

    return [staff_to_response(s, db) for s in staff_list]


@router.get("/by-email/{email}", response_model=StaffProfileResponse)
async def get_staff_by_email(
    email: str,
    db: Session = Depends(get_db),
):
    """Get a staff profile by email address"""
    service = StaffService(db)
    staff = service.get_staff_by_email(email)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff_to_response(staff, db)


@router.get("/{staff_id}", response_model=StaffProfileResponse)
async def get_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a specific staff profile by ID"""
    service = StaffService(db)
    staff = service.get_staff(staff_id)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff_to_response(staff, db)


@router.patch("/{staff_id}", response_model=StaffProfileResponse)
async def update_staff(
    staff_id: UUID,
    update_data: StaffProfileUpdate,
    db: Session = Depends(get_db),
):
    """Update a staff profile"""
    service = StaffService(db)
    staff = service.update_staff(staff_id, update_data)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff_to_response(staff, db)


@router.delete("/{staff_id}", status_code=204)
async def delete_staff(
    staff_id: UUID,
    db: Session = Depends(get_db),
):
    """Delete a staff profile"""
    service = StaffService(db)
    success = service.delete_staff(staff_id)

    if not success:
        raise HTTPException(status_code=404, detail="Staff not found")

    return None


# =============================================================================
# DUTY STATUS
# =============================================================================

@router.post("/{staff_id}/duty", response_model=StaffProfileResponse)
async def update_duty_status(
    staff_id: UUID,
    on_duty: bool = Query(..., description="New on-duty status"),
    db: Session = Depends(get_db),
):
    """Update a staff member's on-duty status"""
    service = StaffService(db)
    staff = service.update_duty_status(staff_id, on_duty)

    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    return staff_to_response(staff, db)


# =============================================================================
# LOCATION TRACKING
# =============================================================================

@router.post("/{staff_id}/location", response_model=StaffLocationResponse)
async def update_location(
    staff_id: UUID,
    location_data: StaffLocationUpdate,
    db: Session = Depends(get_db),
):
    """Update a staff member's current location"""
    service = StaffService(db)
    location = service.update_location(staff_id, location_data)

    if not location:
        raise HTTPException(status_code=404, detail="Staff not found")

    return StaffLocationResponse(
        id=location.id,
        staff_id=location.staff_id,
        zone_id=location.zone_id,
        building=location.building,
        floor=location.floor,
        source=location.source,
        timestamp=location.timestamp,
    )


@router.get("/{staff_id}/location", response_model=Optional[StaffLocationResponse])
async def get_current_location(
    staff_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a staff member's current location"""
    service = StaffService(db)

    # Verify staff exists
    staff = service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    location = service.get_current_location(staff_id)

    if not location:
        return None

    return StaffLocationResponse(
        id=location.id,
        staff_id=location.staff_id,
        zone_id=location.zone_id,
        building=location.building,
        floor=location.floor,
        source=location.source,
        timestamp=location.timestamp,
    )


@router.get("/{staff_id}/location/history", response_model=List[StaffLocationResponse])
async def get_location_history(
    staff_id: UUID,
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db),
):
    """Get a staff member's recent location history"""
    service = StaffService(db)

    # Verify staff exists
    staff = service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    locations = service.get_location_history(staff_id, limit=limit)

    return [
        StaffLocationResponse(
            id=loc.id,
            staff_id=loc.staff_id,
            zone_id=loc.zone_id,
            building=loc.building,
            floor=loc.floor,
            source=loc.source,
            timestamp=loc.timestamp,
        )
        for loc in locations
    ]


# =============================================================================
# ZONE-BASED QUERIES
# =============================================================================

@router.get("/zone/{zone_id}", response_model=List[StaffProfileResponse])
async def get_staff_in_zone(
    zone_id: str,
    db: Session = Depends(get_db),
):
    """Get all staff currently in a specific zone"""
    service = StaffService(db)
    staff_list = service.get_staff_in_zone(zone_id)

    return [staff_to_response(s, db) for s in staff_list]


# =============================================================================
# STATISTICS
# =============================================================================

@router.get("/{staff_id}/stats")
async def get_staff_statistics(
    staff_id: UUID,
    db: Session = Depends(get_db),
):
    """Get statistics for a staff member"""
    service = StaffService(db)
    stats = service.get_staff_statistics(staff_id)

    if not stats:
        raise HTTPException(status_code=404, detail="Staff not found")

    return stats


# =============================================================================
# STAFF DASHBOARD & WORKFLOW ENDPOINTS
# =============================================================================

@router.get("/{staff_id}/dashboard")
async def get_staff_dashboard(
    staff_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Get a comprehensive dashboard for a staff member.

    Includes:
    - Profile info
    - Current location
    - Active alerts assigned to them
    - Recent activity
    - Statistics
    """
    staff_service = StaffService(db)
    alert_service = AlertService(db)

    # Get staff profile
    staff = staff_service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Get current location
    location = staff_service.get_current_location(staff_id)

    # Get active alerts assigned to this staff
    active_alerts = alert_service.get_alerts_for_staff(staff_id, active_only=True)

    # Get recent activity (alerts resolved in last 24 hours)
    from datetime import datetime, timedelta
    recent_alerts = alert_service.get_alerts_for_staff(
        staff_id,
        active_only=False,
        since=datetime.utcnow() - timedelta(hours=24)
    )

    # Get statistics
    stats = staff_service.get_staff_statistics(staff_id)

    return {
        "staff": staff_to_response(staff, db),
        "current_location": {
            "zone_id": location.zone_id if location else None,
            "building": location.building if location else None,
            "floor": location.floor if location else None,
            "last_update": location.timestamp if location else None,
        },
        "active_alerts": [
            {
                "id": str(a.id),
                "title": a.title,
                "severity": a.severity.value,
                "status": a.status.value,
                "location": a.location,
                "created_at": a.created_at,
                "assigned_at": a.assigned_at,
                "acknowledged_at": a.acknowledged_at,
            }
            for a in active_alerts
        ],
        "recent_activity": {
            "alerts_handled_24h": len([a for a in recent_alerts if a.status == AlertStatus.RESOLVED]),
            "alerts_pending": len([a for a in active_alerts if a.status == AlertStatus.ASSIGNED]),
            "alerts_investigating": len([a for a in active_alerts if a.status == AlertStatus.INVESTIGATING]),
        },
        "statistics": stats,
    }


@router.get("/{staff_id}/alerts")
async def get_staff_alerts(
    staff_id: UUID,
    status: Optional[AlertStatusEnum] = Query(None, description="Filter by status"),
    active_only: bool = Query(True, description="Only show active (non-resolved) alerts"),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """
    Get all alerts assigned to a staff member.

    Can filter by status and active/all alerts.
    """
    staff_service = StaffService(db)
    alert_service = AlertService(db)

    # Verify staff exists
    staff = staff_service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    alerts = alert_service.get_alerts_for_staff(
        staff_id=staff_id,
        status=AlertStatus(status.value) if status else None,
        active_only=active_only,
        limit=limit,
    )

    return {
        "staff_id": str(staff_id),
        "staff_name": staff.name,
        "total": len(alerts),
        "alerts": [
            {
                "id": str(a.id),
                "title": a.title,
                "description": a.description,
                "severity": a.severity.value,
                "status": a.status.value,
                "anomaly_type": a.anomaly_type,
                "location": a.location,
                "created_at": a.created_at,
                "assigned_at": a.assigned_at,
                "acknowledged_at": a.acknowledged_at,
                "escalation_count": a.escalation_count,
            }
            for a in alerts
        ],
    }


@router.post("/{staff_id}/alerts/{alert_id}/start-investigation")
async def start_investigation(
    staff_id: UUID,
    alert_id: UUID,
    notes: Optional[str] = Query(None, description="Initial investigation notes"),
    db: Session = Depends(get_db),
):
    """
    Start investigating an alert.

    Updates the alert status to 'investigating' and optionally adds initial notes.
    This is typically done after acknowledging the alert.
    """
    staff_service = StaffService(db)
    alert_service = AlertService(db)

    # Verify staff exists
    staff = staff_service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Get the alert
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Verify this staff is assigned to the alert
    if alert.assigned_to != staff_id:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this alert"
        )

    # Update status to investigating
    try:
        alert = alert_service.update_status(
            alert_id=alert_id,
            new_status=AlertStatusEnum.INVESTIGATING,
            updated_by=staff_id,
            actor_type=ActorType.STAFF,
            notes=notes or "Started investigation",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "message": "Investigation started",
        "alert_id": str(alert_id),
        "status": alert.status.value,
        "staff_id": str(staff_id),
    }


@router.post("/{staff_id}/alerts/{alert_id}/request-backup")
async def request_backup(
    staff_id: UUID,
    alert_id: UUID,
    reason: str = Query(..., description="Reason for requesting backup"),
    db: Session = Depends(get_db),
):
    """
    Request backup for an alert.

    Assigns additional staff to help with the alert and sends notifications.
    """
    staff_service = StaffService(db)
    alert_service = AlertService(db)
    notification_service = NotificationService(db)
    assignment_engine = AssignmentEngine(db)

    # Verify staff exists
    staff = staff_service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Get the alert
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Verify this staff is assigned to the alert
    if alert.assigned_to != staff_id:
        raise HTTPException(
            status_code=403,
            detail="You are not assigned to this alert"
        )

    # Find backup staff
    backup_staff = assignment_engine.find_escalation_target(
        alert=alert,
        current_assignee=staff_id,
    )

    if not backup_staff:
        raise HTTPException(
            status_code=400,
            detail="No backup staff available"
        )

    # Log the backup request
    from services.alerts import AuditService
    from models.db.alerts import AuditAction
    audit_service = AuditService(db)
    audit_service.log_action(
        alert_id=alert_id,
        action=AuditAction.BACKUP_REQUESTED,
        actor_id=staff_id,
        actor_type=ActorType.STAFF,
        details={
            "reason": reason,
            "backup_staff_id": str(backup_staff.id),
            "backup_staff_name": backup_staff.name,
        },
    )

    # Send notification to backup staff
    notification_service.notify_staff_of_assignment(
        staff=backup_staff,
        alert=alert,
        is_critical=True,
    )

    # Process the notification immediately
    notification_service.process_queue(batch_size=5)

    return {
        "message": "Backup requested successfully",
        "alert_id": str(alert_id),
        "backup_staff": {
            "id": str(backup_staff.id),
            "name": backup_staff.name,
            "role": backup_staff.role.value if hasattr(backup_staff.role, 'value') else backup_staff.role,
        },
        "reason": reason,
    }


@router.post("/{staff_id}/alerts/{alert_id}/add-note")
async def staff_add_note(
    staff_id: UUID,
    alert_id: UUID,
    note: str = Query(..., min_length=1, description="Note content"),
    db: Session = Depends(get_db),
):
    """
    Add a note to an alert during investigation.

    Staff can add progress updates, observations, or other notes.
    """
    staff_service = StaffService(db)
    alert_service = AlertService(db)

    # Verify staff exists
    staff = staff_service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Get the alert
    alert = alert_service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    # Add the note
    alert = alert_service.add_note(
        alert_id=alert_id,
        note=note,
        added_by=staff_id,
    )

    return {
        "message": "Note added successfully",
        "alert_id": str(alert_id),
        "staff_id": str(staff_id),
        "note": note,
    }


@router.post("/{staff_id}/go-off-duty")
async def go_off_duty(
    staff_id: UUID,
    reassign_alerts: bool = Query(True, description="Reassign active alerts to other staff"),
    db: Session = Depends(get_db),
):
    """
    Mark staff as off duty.

    Optionally reassigns their active alerts to other available staff.
    """
    staff_service = StaffService(db)
    alert_service = AlertService(db)
    assignment_engine = AssignmentEngine(db)

    # Verify staff exists
    staff = staff_service.get_staff(staff_id)
    if not staff:
        raise HTTPException(status_code=404, detail="Staff not found")

    # Get active alerts
    active_alerts = alert_service.get_alerts_for_staff(staff_id, active_only=True)

    reassigned_alerts = []

    if reassign_alerts and active_alerts:
        for alert in active_alerts:
            # Find new assignee
            new_assignee = assignment_engine.assign_alert(
                alert=alert,
                exclude_staff_ids=[staff_id],
            )
            if new_assignee:
                reassigned_alerts.append({
                    "alert_id": str(alert.id),
                    "alert_title": alert.title,
                    "new_assignee": new_assignee.name,
                })

    # Update duty status
    staff_service.update_duty_status(staff_id, on_duty=False)

    return {
        "message": "Successfully went off duty",
        "staff_id": str(staff_id),
        "reassigned_alerts": reassigned_alerts,
        "unassigned_alerts": len(active_alerts) - len(reassigned_alerts),
    }
