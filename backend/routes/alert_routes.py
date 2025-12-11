"""
Alert API Routes
Provides REST endpoints for alert management.
"""

import logging
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from services.alerts import AlertService, AuditService, AssignmentEngine, run_escalation_check
from models.db.alerts import AlertSeverity, AlertStatus
from models.schemas.alerts import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse,
    AlertStatusUpdate,
    AlertResolve,
    AlertAssignmentCreate,
    AlertAssignmentResponse,
    AuditLogResponse,
    AuditLogListResponse,
    AlertStatusEnum,
    AlertSeverityEnum,
    ActorTypeEnum,
)
from models.db.alerts import ActorType

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])


def get_client_info(request: Request) -> tuple:
    """Extract client IP and user agent from request"""
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    return ip_address, user_agent


def alert_to_response(alert, db: Session) -> AlertResponse:
    """Convert Alert model to AlertResponse schema"""
    from models.db.alerts import StaffProfile

    assigned_staff_name = None
    resolver_name = None

    if alert.assigned_to:
        staff = db.query(StaffProfile).filter(StaffProfile.id == alert.assigned_to).first()
        if staff:
            assigned_staff_name = staff.name

    if alert.resolved_by:
        resolver = db.query(StaffProfile).filter(StaffProfile.id == alert.resolved_by).first()
        if resolver:
            resolver_name = resolver.name

    return AlertResponse(
        id=alert.id,
        anomaly_id=alert.anomaly_id,
        anomaly_type=alert.anomaly_type,
        title=alert.title,
        description=alert.description,
        severity=AlertSeverityEnum(alert.severity.value),
        status=AlertStatusEnum(alert.status.value),
        location=alert.location,
        affected_entities=alert.affected_entities,
        data_sources=alert.data_sources,
        evidence=alert.evidence,
        assigned_to=alert.assigned_to,
        assigned_at=alert.assigned_at,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        resolved_by=alert.resolved_by,
        resolution_type=alert.resolution_type.value if alert.resolution_type else None,
        resolution_notes=alert.resolution_notes,
        escalation_count=alert.escalation_count,
        is_mock=alert.is_mock,
        mock_scenario=alert.mock_scenario,
        created_at=alert.created_at,
        updated_at=alert.updated_at,
        assigned_staff_name=assigned_staff_name,
        resolver_name=resolver_name,
    )


# =============================================================================
# ALERT CRUD ENDPOINTS
# =============================================================================

@router.post("", response_model=AlertResponse, status_code=201)
async def create_alert(
    alert_data: AlertCreate,
    request: Request,
    auto_assign: bool = Query(True, description="Automatically assign to nearest available staff"),
    db: Session = Depends(get_db),
):
    """
    Create a new alert.

    This endpoint is typically called by the anomaly detection system
    when a new anomaly is detected.

    By default, the alert is automatically assigned to the nearest available
    staff member. Set `auto_assign=false` to create without assignment.

    For critical alerts, multiple staff members may be notified.
    """
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    alert = service.create_alert(
        alert_data=alert_data,
        actor_type=ActorType.SYSTEM,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    # Auto-assign if requested and not a mock alert (mock alerts are handled by demo system)
    if auto_assign and not alert_data.is_mock:
        assignment_engine = AssignmentEngine(db)

        if alert.severity == AlertSeverity.CRITICAL:
            # Critical alerts get multiple assignees
            assigned_staff = assignment_engine.assign_critical_alert(alert, max_assignees=3)
            if assigned_staff:
                logger.info(f"Critical alert {alert.id} auto-assigned to {len(assigned_staff)} staff")
        else:
            # Normal alerts get single assignee
            assigned_staff = assignment_engine.assign_alert(alert)
            if assigned_staff:
                logger.info(f"Alert {alert.id} auto-assigned to {assigned_staff.name}")

        # Refresh alert to get updated assignment info
        db.refresh(alert)

    return alert_to_response(alert, db)


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[AlertStatusEnum] = Query(None, description="Filter by status"),
    severity: Optional[AlertSeverityEnum] = Query(None, description="Filter by severity"),
    zone_id: Optional[str] = Query(None, description="Filter by zone"),
    assigned_to: Optional[UUID] = Query(None, description="Filter by assigned staff"),
    is_mock: Optional[bool] = Query(None, description="Filter by mock flag"),
    include_resolved: bool = Query(False, description="Include resolved alerts"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    db: Session = Depends(get_db),
):
    """
    List alerts with optional filters.

    By default, resolved alerts are excluded. Use `include_resolved=true` to include them.
    Results are ordered by severity (critical first) and then by creation time.
    """
    service = AlertService(db)
    alerts, total = service.get_alerts(
        status=status,
        severity=severity,
        zone_id=zone_id,
        assigned_to=assigned_to,
        is_mock=is_mock,
        include_resolved=include_resolved,
        limit=limit,
        offset=offset,
    )

    return AlertListResponse(
        alerts=[alert_to_response(a, db) for a in alerts],
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + len(alerts)) < total,
    )


@router.get("/active", response_model=AlertListResponse)
async def list_active_alerts(
    severity: Optional[AlertSeverityEnum] = Query(None, description="Filter by severity"),
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    db: Session = Depends(get_db),
):
    """
    List all active (non-resolved) alerts.

    Convenience endpoint for dashboards - excludes resolved alerts and mock alerts.
    """
    service = AlertService(db)
    alerts, total = service.get_alerts(
        severity=severity,
        is_mock=False,
        include_resolved=False,
        limit=limit,
        offset=0,
    )

    return AlertListResponse(
        alerts=[alert_to_response(a, db) for a in alerts],
        total=total,
        offset=0,
        limit=limit,
        has_more=False,
    )


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
):
    """Get a specific alert by ID"""
    service = AlertService(db)
    alert = service.get_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: UUID,
    update_data: AlertUpdate,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Update an alert's basic information.

    This endpoint allows updating title, description, severity, location, and evidence.
    Use specific endpoints for status changes, assignments, and resolution.
    """
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    alert = service.update_alert(
        alert_id=alert_id,
        update_data=update_data,
        actor_type=ActorType.ADMIN,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


@router.delete("/{alert_id}", status_code=204)
async def delete_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Delete an alert.

    This is a hard delete - use with caution. For normal workflow,
    use the resolve endpoint instead.
    """
    service = AlertService(db)
    success = service.delete_alert(alert_id)

    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")

    return None


# =============================================================================
# ALERT STATUS & LIFECYCLE ENDPOINTS
# =============================================================================

@router.post("/{alert_id}/status", response_model=AlertResponse)
async def update_alert_status(
    alert_id: UUID,
    status_update: AlertStatusUpdate,
    request: Request,
    staff_id: Optional[UUID] = Query(None, description="Staff ID making the update"),
    db: Session = Depends(get_db),
):
    """
    Update an alert's status.

    Valid transitions:
    - created -> assigned, escalated
    - assigned -> acknowledged, escalated
    - acknowledged -> investigating, resolved, escalated
    - investigating -> resolved, escalated
    - escalated -> assigned, resolved
    """
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    try:
        alert = service.update_status(
            alert_id=alert_id,
            new_status=status_update.status,
            updated_by=staff_id,
            actor_type=ActorType.STAFF if staff_id else ActorType.SYSTEM,
            notes=status_update.notes,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


@router.post("/{alert_id}/assign", response_model=AlertResponse)
async def assign_alert(
    alert_id: UUID,
    assignment: AlertAssignmentCreate,
    request: Request,
    assigned_by: Optional[UUID] = Query(None, description="Admin ID making the assignment"),
    db: Session = Depends(get_db),
):
    """
    Assign an alert to a staff member.

    This endpoint is used for manual assignment by admins.
    Automatic assignment is handled by the assignment engine.
    """
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    try:
        alert = service.assign_alert(
            alert_id=alert_id,
            staff_id=assignment.staff_id,
            assigned_by=assigned_by,
            actor_type=ActorType.ADMIN if assigned_by else ActorType.SYSTEM,
            reason=assignment.assignment_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


@router.post("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: UUID,
    staff_id: UUID = Query(..., description="Staff ID acknowledging the alert"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Acknowledge an alert (staff action).

    Only the assigned staff member can acknowledge an alert.
    """
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    try:
        alert = service.acknowledge_alert(
            alert_id=alert_id,
            staff_id=staff_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


@router.post("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: UUID,
    resolution: AlertResolve,
    staff_id: UUID = Query(..., description="Staff ID resolving the alert"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Resolve an alert.

    Requires a resolution type and notes explaining the outcome.
    """
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    alert = service.resolve_alert(
        alert_id=alert_id,
        resolved_by=staff_id,
        resolution_type=resolution.resolution_type,
        resolution_notes=resolution.resolution_notes,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


@router.post("/{alert_id}/escalate", response_model=AlertResponse)
async def escalate_alert(
    alert_id: UUID,
    escalate_to: UUID = Query(..., description="Staff ID to escalate to"),
    reason: str = Query(..., description="Reason for escalation"),
    escalated_by: Optional[UUID] = Query(None, description="Staff ID initiating escalation"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """
    Escalate an alert to a supervisor or admin.

    Can be triggered manually or by the escalation system.
    """
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    alert = service.escalate_alert(
        alert_id=alert_id,
        escalate_to=escalate_to,
        reason=reason,
        escalated_by=escalated_by,
        actor_type=ActorType.STAFF if escalated_by else ActorType.SYSTEM,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


@router.post("/{alert_id}/notes", response_model=AlertResponse)
async def add_note(
    alert_id: UUID,
    note: str = Query(..., description="Note content"),
    staff_id: UUID = Query(..., description="Staff ID adding the note"),
    request: Request = None,
    db: Session = Depends(get_db),
):
    """Add a note to an alert"""
    ip_address, user_agent = get_client_info(request)

    service = AlertService(db)
    alert = service.add_note(
        alert_id=alert_id,
        note=note,
        added_by=staff_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    return alert_to_response(alert, db)


# =============================================================================
# AUDIT LOG ENDPOINTS
# =============================================================================

@router.get("/{alert_id}/audit", response_model=AuditLogListResponse)
async def get_alert_audit_trail(
    alert_id: UUID,
    limit: int = Query(50, ge=1, le=100, description="Maximum results"),
    offset: int = Query(0, ge=0, description="Results to skip"),
    db: Session = Depends(get_db),
):
    """
    Get the complete audit trail for an alert.

    Returns all actions taken on the alert in reverse chronological order.
    """
    # First verify alert exists
    service = AlertService(db)
    alert = service.get_alert(alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    audit_service = AuditService(db)
    logs = audit_service.get_alert_audit_trail(alert_id, limit=limit, offset=offset)
    total = audit_service.get_audit_count(alert_id)

    # Convert to response format
    from models.db.alerts import StaffProfile

    log_responses = []
    for log in logs:
        actor_name = None
        if log.actor_id:
            actor = db.query(StaffProfile).filter(StaffProfile.id == log.actor_id).first()
            if actor:
                actor_name = actor.name

        log_responses.append(AuditLogResponse(
            id=log.id,
            alert_id=log.alert_id,
            action=log.action,
            actor_id=log.actor_id,
            actor_type=log.actor_type,
            actor_name=actor_name,
            details=log.details,
            ip_address=log.ip_address,
            is_mock=log.is_mock,
            timestamp=log.timestamp,
        ))

    return AuditLogListResponse(
        logs=log_responses,
        total=total,
        offset=offset,
        limit=limit,
        has_more=(offset + len(logs)) < total,
    )


# =============================================================================
# UTILITY ENDPOINTS
# =============================================================================

@router.delete("/mock", status_code=200)
async def clear_mock_alerts(
    db: Session = Depends(get_db),
):
    """
    Clear all mock/demo alerts.

    Used for cleaning up after demo sessions.
    """
    service = AlertService(db)
    count = service.clear_mock_alerts()

    return {"message": f"Cleared {count} mock alerts", "count": count}


@router.get("/staff/{staff_id}/active", response_model=AlertListResponse)
async def get_staff_active_alerts(
    staff_id: UUID,
    db: Session = Depends(get_db),
):
    """Get all active alerts assigned to a specific staff member"""
    service = AlertService(db)
    alerts = service.get_active_alerts_for_staff(staff_id)

    return AlertListResponse(
        alerts=[alert_to_response(a, db) for a in alerts],
        total=len(alerts),
        offset=0,
        limit=len(alerts),
        has_more=False,
    )


# =============================================================================
# ASSIGNMENT ENGINE ENDPOINTS
# =============================================================================

@router.post("/{alert_id}/auto-assign", response_model=AlertResponse)
async def auto_assign_alert(
    alert_id: UUID,
    db: Session = Depends(get_db),
):
    """
    Automatically assign an alert to the best available staff member.

    Uses the assignment engine to find the optimal staff member based on:
    - Proximity to alert location
    - Current workload
    - Role/skill match for alert type
    """
    service = AlertService(db)
    alert = service.get_alert(alert_id)

    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == AlertStatus.RESOLVED:
        raise HTTPException(status_code=400, detail="Cannot assign resolved alert")

    assignment_engine = AssignmentEngine(db)

    if alert.severity == AlertSeverity.CRITICAL:
        assigned_staff = assignment_engine.assign_critical_alert(alert, max_assignees=3)
        if not assigned_staff:
            raise HTTPException(status_code=400, detail="No available staff for assignment")
    else:
        assigned_staff = assignment_engine.assign_alert(alert)
        if not assigned_staff:
            raise HTTPException(status_code=400, detail="No available staff for assignment")

    db.refresh(alert)
    return alert_to_response(alert, db)


@router.post("/escalation-check", status_code=200)
async def trigger_escalation_check(
    db: Session = Depends(get_db),
):
    """
    Trigger the escalation check manually.

    This endpoint runs the escalation checker to find alerts that need
    escalation due to:
    - No acknowledgment within timeout
    - No resolution within timeout

    In production, this would typically be run by a background scheduler.
    """
    results = run_escalation_check(db)

    return {
        "message": "Escalation check complete",
        "results": results,
    }


@router.get("/assignment/candidates/{zone_id}")
async def get_assignment_candidates(
    zone_id: str,
    alert_type: Optional[str] = Query(None, description="Alert type for skill matching"),
    db: Session = Depends(get_db),
):
    """
    Get ranked list of staff candidates for assignment to a zone.

    Useful for understanding who would be assigned and why.
    """
    from services.alerts import StaffService

    assignment_engine = AssignmentEngine(db)
    staff_service = StaffService(db)

    # Get adjacent zones
    adjacent_zones = assignment_engine._get_adjacent_zones(zone_id, max_distance=3)

    # Get candidates
    candidates = assignment_engine._get_candidates(
        zone_id=zone_id,
        alert_type=alert_type,
        severity=AlertSeverity.MEDIUM,
        exclude_ids=[],
    )

    # Score candidates
    if candidates:
        scored = assignment_engine._score_candidates(
            candidates=candidates,
            zone_id=zone_id,
            alert_type=alert_type,
            severity=AlertSeverity.MEDIUM,
        )

        result = []
        for staff, score, details in scored:
            stats = staff_service.get_staff_statistics(staff.id)
            result.append({
                "staff_id": str(staff.id),
                "name": staff.name,
                "role": staff.role.value,
                "score": round(score, 3),
                "current_zone": details.get("current_zone"),
                "zone_distance": details.get("zone_distance"),
                "proximity_score": round(details.get("proximity_score", 0), 3),
                "workload_score": round(details.get("workload_score", 0), 3),
                "skill_score": round(details.get("skill_score", 0), 3),
                "active_alerts": stats.get("active_alerts", 0),
                "available_capacity": stats.get("available_capacity", 0),
            })
    else:
        result = []

    return {
        "zone_id": zone_id,
        "adjacent_zones": adjacent_zones,
        "alert_type": alert_type,
        "candidates": result,
        "total_candidates": len(result),
    }
