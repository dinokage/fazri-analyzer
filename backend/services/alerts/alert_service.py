"""
Alert Service for managing security alerts.
Handles alert CRUD operations, status transitions, and lifecycle management.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc

from models.db.alerts import (
    Alert,
    AlertAssignment,
    AlertStatus,
    AlertSeverity,
    ResolutionType,
    StaffProfile,
    ActorType,
)
from models.schemas.alerts import (
    AlertCreate,
    AlertUpdate,
    AlertStatusEnum,
    AlertSeverityEnum,
    ResolutionTypeEnum,
)
from .audit_service import AuditService
from config import settings

logger = logging.getLogger(__name__)


class AlertService:
    """Service for managing security alerts"""

    # Valid status transitions
    VALID_TRANSITIONS = {
        AlertStatus.CREATED: [AlertStatus.ASSIGNED, AlertStatus.ESCALATED],
        AlertStatus.ASSIGNED: [AlertStatus.ACKNOWLEDGED, AlertStatus.ESCALATED, AlertStatus.ASSIGNED],  # Can reassign
        AlertStatus.ACKNOWLEDGED: [AlertStatus.INVESTIGATING, AlertStatus.RESOLVED, AlertStatus.ESCALATED],
        AlertStatus.INVESTIGATING: [AlertStatus.RESOLVED, AlertStatus.ESCALATED],
        AlertStatus.ESCALATED: [AlertStatus.ASSIGNED, AlertStatus.RESOLVED],
        AlertStatus.RESOLVED: [],  # Terminal state
    }

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def create_alert(
        self,
        alert_data: AlertCreate,
        created_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Alert:
        """
        Create a new alert.

        Args:
            alert_data: Alert creation data
            created_by: UUID of the creator (None for system)
            actor_type: Type of actor creating the alert
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The created alert
        """
        # Convert location schema to dict
        location_dict = alert_data.location.model_dump()

        alert = Alert(
            anomaly_id=alert_data.anomaly_id,
            anomaly_type=alert_data.anomaly_type,
            title=alert_data.title,
            description=alert_data.description,
            severity=AlertSeverity(alert_data.severity.value),
            status=AlertStatus.CREATED,
            location=location_dict,
            affected_entities=alert_data.affected_entities,
            data_sources=alert_data.data_sources,
            evidence=alert_data.evidence,
            is_mock=alert_data.is_mock,
            mock_scenario=alert_data.mock_scenario,
        )

        self.db.add(alert)
        self.db.flush()

        # Log the creation
        self.audit_service.log_alert_created(
            alert_id=alert.id,
            created_by=created_by,
            actor_type=actor_type,
            details={
                "title": alert.title,
                "severity": alert.severity.value,
                "location": location_dict,
                "anomaly_id": alert.anomaly_id,
            },
            is_mock=alert.is_mock,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert created: id={alert.id}, title={alert.title}, severity={alert.severity.value}")

        return alert

    def get_alert(self, alert_id: UUID, include_assignments: bool = False) -> Optional[Alert]:
        """
        Get an alert by ID.

        Args:
            alert_id: The alert ID
            include_assignments: Whether to eagerly load assignments

        Returns:
            The alert or None if not found
        """
        query = self.db.query(Alert)

        if include_assignments:
            query = query.options(
                joinedload(Alert.assignments),
                joinedload(Alert.assigned_staff),
            )

        return query.filter(Alert.id == alert_id).first()

    def get_alerts(
        self,
        status: Optional[AlertStatusEnum] = None,
        severity: Optional[AlertSeverityEnum] = None,
        zone_id: Optional[str] = None,
        assigned_to: Optional[UUID] = None,
        is_mock: Optional[bool] = None,
        include_resolved: bool = False,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Alert], int]:
        """
        Get alerts with optional filters.

        Args:
            status: Filter by status
            severity: Filter by severity
            zone_id: Filter by zone
            assigned_to: Filter by assigned staff
            is_mock: Filter by mock flag
            include_resolved: Include resolved alerts
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (alerts list, total count)
        """
        query = self.db.query(Alert)

        # Apply filters
        if status:
            query = query.filter(Alert.status == AlertStatus(status.value))
        elif not include_resolved:
            query = query.filter(Alert.status != AlertStatus.RESOLVED)

        if severity:
            query = query.filter(Alert.severity == AlertSeverity(severity.value))

        if zone_id:
            # Filter by zone_id in JSON location field
            query = query.filter(Alert.location["zone_id"].astext == zone_id)

        if assigned_to:
            query = query.filter(Alert.assigned_to == assigned_to)

        if is_mock is not None:
            query = query.filter(Alert.is_mock == is_mock)

        # Get total count before pagination
        total = query.count()

        # Apply ordering and pagination
        alerts = (
            query
            .order_by(
                # Critical first, then by created_at
                desc(Alert.severity == AlertSeverity.CRITICAL),
                desc(Alert.severity == AlertSeverity.HIGH),
                desc(Alert.created_at)
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

        return alerts, total

    def get_alerts_for_staff(
        self,
        staff_id: UUID,
        status: Optional[AlertStatus] = None,
        active_only: bool = True,
        since: Optional[datetime] = None,
        limit: int = 50,
    ) -> List[Alert]:
        """
        Get alerts assigned to a specific staff member.

        Args:
            staff_id: Staff member's UUID
            status: Filter by specific status
            active_only: If True, exclude resolved alerts
            since: Only include alerts created after this time
            limit: Maximum number of results

        Returns:
            List of alerts assigned to the staff member
        """
        query = self.db.query(Alert).filter(Alert.assigned_to == staff_id)

        if status:
            query = query.filter(Alert.status == status)
        elif active_only:
            query = query.filter(Alert.status != AlertStatus.RESOLVED)

        if since:
            query = query.filter(Alert.created_at >= since)

        return (
            query
            .order_by(
                desc(Alert.severity == AlertSeverity.CRITICAL),
                desc(Alert.severity == AlertSeverity.HIGH),
                desc(Alert.created_at)
            )
            .limit(limit)
            .all()
        )

    def update_alert(
        self,
        alert_id: UUID,
        update_data: AlertUpdate,
        updated_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.ADMIN,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        Update an alert's basic information.

        Args:
            alert_id: The alert to update
            update_data: The update data
            updated_by: UUID of the updater
            actor_type: Type of actor updating
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The updated alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None

        changes = {}

        if update_data.title is not None:
            changes["title"] = {"from": alert.title, "to": update_data.title}
            alert.title = update_data.title

        if update_data.description is not None:
            changes["description"] = {"from": alert.description[:100], "to": update_data.description[:100]}
            alert.description = update_data.description

        if update_data.severity is not None:
            old_severity = alert.severity.value
            new_severity = update_data.severity.value
            if old_severity != new_severity:
                alert.severity = AlertSeverity(new_severity)
                self.audit_service.log_severity_change(
                    alert_id=alert_id,
                    previous_severity=old_severity,
                    new_severity=new_severity,
                    changed_by=updated_by,
                    actor_type=actor_type,
                    is_mock=alert.is_mock,
                    ip_address=ip_address,
                    user_agent=user_agent,
                )

        if update_data.location is not None:
            changes["location"] = {"from": alert.location, "to": update_data.location.model_dump()}
            alert.location = update_data.location.model_dump()

        if update_data.evidence is not None:
            alert.evidence = {**alert.evidence, **update_data.evidence}

        alert.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert updated: id={alert_id}, changes={list(changes.keys())}")

        return alert

    def update_status(
        self,
        alert_id: UUID,
        new_status: AlertStatusEnum,
        updated_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.STAFF,
        notes: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        Update an alert's status with validation.

        Args:
            alert_id: The alert to update
            new_status: The new status
            updated_by: UUID of the updater
            actor_type: Type of actor updating
            notes: Optional notes for the status change
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The updated alert or None if not found

        Raises:
            ValueError: If the status transition is not valid
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None

        # Validate transition
        new_status_enum = AlertStatus(new_status.value)
        valid_next = self.VALID_TRANSITIONS.get(alert.status, [])

        # Allow same status (no-op)
        if alert.status == new_status_enum:
            return alert

        if new_status_enum not in valid_next:
            raise ValueError(
                f"Invalid status transition: {alert.status.value} -> {new_status.value}. "
                f"Valid transitions: {[s.value for s in valid_next]}"
            )

        old_status = alert.status.value
        alert.status = new_status_enum
        alert.updated_at = datetime.utcnow()

        # Handle specific status updates
        if new_status_enum == AlertStatus.ACKNOWLEDGED:
            alert.acknowledged_at = datetime.utcnow()
            self.audit_service.log_alert_acknowledged(
                alert_id=alert_id,
                acknowledged_by=updated_by,
                is_mock=alert.is_mock,
                ip_address=ip_address,
                user_agent=user_agent,
            )
        else:
            self.audit_service.log_status_change(
                alert_id=alert_id,
                previous_status=old_status,
                new_status=new_status.value,
                changed_by=updated_by,
                actor_type=actor_type,
                notes=notes,
                is_mock=alert.is_mock,
                ip_address=ip_address,
                user_agent=user_agent,
            )

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert status updated: id={alert_id}, {old_status} -> {new_status.value}")

        return alert

    def assign_alert(
        self,
        alert_id: UUID,
        staff_id: UUID,
        assigned_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        reason: str = "auto",
        proximity_score: Optional[float] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        Assign an alert to a staff member.

        Args:
            alert_id: The alert to assign
            staff_id: The staff member to assign to
            assigned_by: UUID of who is making the assignment
            actor_type: Type of actor making assignment
            reason: Reason for assignment
            proximity_score: Proximity score if auto-assigned
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The updated alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None

        # Verify staff exists
        staff = self.db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()
        if not staff:
            raise ValueError(f"Staff not found: {staff_id}")

        # Deactivate previous assignment if exists
        if alert.assigned_to:
            prev_assignment = (
                self.db.query(AlertAssignment)
                .filter(
                    AlertAssignment.alert_id == alert_id,
                    AlertAssignment.is_active == True
                )
                .first()
            )
            if prev_assignment:
                prev_assignment.is_active = False
                prev_assignment.completed_at = datetime.utcnow()

        # Create new assignment record
        assignment = AlertAssignment(
            alert_id=alert_id,
            staff_id=staff_id,
            assignment_reason=reason,
            proximity_score=proximity_score,
            is_active=True,
        )
        self.db.add(assignment)

        # Update alert
        alert.assigned_to = staff_id
        alert.assigned_at = datetime.utcnow()

        # Update status if still in CREATED
        if alert.status == AlertStatus.CREATED:
            alert.status = AlertStatus.ASSIGNED

        alert.updated_at = datetime.utcnow()

        # Log the assignment
        self.audit_service.log_alert_assigned(
            alert_id=alert_id,
            assigned_to=staff_id,
            assigned_by=assigned_by,
            actor_type=actor_type,
            reason=reason,
            proximity_score=proximity_score,
            is_mock=alert.is_mock,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert assigned: id={alert_id}, staff={staff_id}, reason={reason}")

        return alert

    def acknowledge_alert(
        self,
        alert_id: UUID,
        staff_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        Acknowledge an alert (staff action).

        Args:
            alert_id: The alert to acknowledge
            staff_id: The staff member acknowledging
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The updated alert or None if not found

        Raises:
            ValueError: If staff is not assigned to this alert
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None

        # Verify staff is assigned
        if alert.assigned_to != staff_id:
            raise ValueError("Only the assigned staff member can acknowledge this alert")

        # Update status
        return self.update_status(
            alert_id=alert_id,
            new_status=AlertStatusEnum.ACKNOWLEDGED,
            updated_by=staff_id,
            actor_type=ActorType.STAFF,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    def resolve_alert(
        self,
        alert_id: UUID,
        resolved_by: UUID,
        resolution_type: ResolutionTypeEnum,
        resolution_notes: str,
        actor_type: ActorType = ActorType.STAFF,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        Resolve an alert.

        Args:
            alert_id: The alert to resolve
            resolved_by: UUID of who is resolving
            resolution_type: Type of resolution
            resolution_notes: Notes about the resolution
            actor_type: Type of actor resolving
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The updated alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None

        # Update alert
        alert.status = AlertStatus.RESOLVED
        alert.resolved_at = datetime.utcnow()
        alert.resolved_by = resolved_by
        alert.resolution_type = ResolutionType(resolution_type.value)
        alert.resolution_notes = resolution_notes
        alert.updated_at = datetime.utcnow()

        # Complete active assignment
        active_assignment = (
            self.db.query(AlertAssignment)
            .filter(
                AlertAssignment.alert_id == alert_id,
                AlertAssignment.is_active == True
            )
            .first()
        )
        if active_assignment:
            active_assignment.is_active = False
            active_assignment.completed_at = datetime.utcnow()

        # Log resolution
        self.audit_service.log_alert_resolved(
            alert_id=alert_id,
            resolved_by=resolved_by,
            resolution_type=resolution_type.value,
            resolution_notes=resolution_notes,
            actor_type=actor_type,
            is_mock=alert.is_mock,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert resolved: id={alert_id}, type={resolution_type.value}")

        return alert

    def escalate_alert(
        self,
        alert_id: UUID,
        escalate_to: UUID,
        reason: str,
        escalated_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        Escalate an alert to a supervisor/admin.

        Args:
            alert_id: The alert to escalate
            escalate_to: The staff member to escalate to
            reason: Reason for escalation
            escalated_by: UUID of who is escalating
            actor_type: Type of actor escalating
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The updated alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None

        # Check escalation limit
        if alert.escalation_count >= settings.ALERT_MAX_ESCALATIONS:
            logger.warning(f"Alert {alert_id} has reached max escalations ({settings.ALERT_MAX_ESCALATIONS})")

        # Update escalation tracking
        alert.escalation_count += 1
        escalation_entry = {
            "escalated_to": str(escalate_to),
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "escalation_number": alert.escalation_count,
        }

        if alert.escalation_history is None:
            alert.escalation_history = []
        alert.escalation_history.append(escalation_entry)

        alert.status = AlertStatus.ESCALATED
        alert.updated_at = datetime.utcnow()

        # Log escalation
        self.audit_service.log_alert_escalated(
            alert_id=alert_id,
            escalated_to=escalate_to,
            reason=reason,
            escalation_count=alert.escalation_count,
            escalated_by=escalated_by,
            actor_type=actor_type,
            is_mock=alert.is_mock,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        # Assign to new staff
        self.assign_alert(
            alert_id=alert_id,
            staff_id=escalate_to,
            assigned_by=escalated_by,
            actor_type=actor_type,
            reason=f"escalation: {reason}",
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Alert escalated: id={alert_id}, to={escalate_to}, count={alert.escalation_count}")

        return alert

    def add_note(
        self,
        alert_id: UUID,
        note: str,
        added_by: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[Alert]:
        """
        Add a note to an alert's evidence.

        Args:
            alert_id: The alert to add note to
            note: The note content
            added_by: UUID of who is adding the note
            ip_address: IP address of the request
            user_agent: User agent string

        Returns:
            The updated alert or None if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return None

        # Add note to evidence
        if "notes" not in alert.evidence:
            alert.evidence["notes"] = []

        alert.evidence["notes"].append({
            "content": note,
            "added_by": str(added_by),
            "timestamp": datetime.utcnow().isoformat(),
        })

        alert.updated_at = datetime.utcnow()

        # Log note addition
        self.audit_service.log_note_added(
            alert_id=alert_id,
            note=note,
            added_by=added_by,
            is_mock=alert.is_mock,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        self.db.commit()
        self.db.refresh(alert)

        logger.info(f"Note added to alert: id={alert_id}")

        return alert

    def get_active_alerts_for_staff(self, staff_id: UUID) -> List[Alert]:
        """Get all active (non-resolved) alerts assigned to a staff member"""
        return (
            self.db.query(Alert)
            .filter(
                Alert.assigned_to == staff_id,
                Alert.status != AlertStatus.RESOLVED,
            )
            .order_by(desc(Alert.created_at))
            .all()
        )

    def get_alert_count_for_staff(self, staff_id: UUID) -> int:
        """Get count of active alerts for a staff member"""
        return (
            self.db.query(Alert)
            .filter(
                Alert.assigned_to == staff_id,
                Alert.status != AlertStatus.RESOLVED,
            )
            .count()
        )

    def delete_alert(self, alert_id: UUID) -> bool:
        """
        Delete an alert (soft delete - just marks as resolved with special type).
        Only for admin use.

        Args:
            alert_id: The alert to delete

        Returns:
            True if deleted, False if not found
        """
        alert = self.get_alert(alert_id)
        if not alert:
            return False

        self.db.delete(alert)
        self.db.commit()

        logger.info(f"Alert deleted: id={alert_id}")

        return True

    def clear_mock_alerts(self) -> int:
        """
        Delete all mock alerts. Used for demo cleanup.

        Returns:
            Number of alerts deleted
        """
        count = self.db.query(Alert).filter(Alert.is_mock == True).delete()
        self.db.commit()

        logger.info(f"Cleared {count} mock alerts")

        return count
