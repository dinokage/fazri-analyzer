"""
Audit Service for tracking all alert-related actions.
Provides immutable audit logging for compliance and investigation.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from uuid import UUID

from sqlalchemy.orm import Session

from models.db.alerts import (
    AlertAuditLog,
    AuditAction,
    ActorType,
)

logger = logging.getLogger(__name__)


class AuditService:
    """Service for managing alert audit logs"""

    def __init__(self, db: Session):
        self.db = db

    def log_action(
        self,
        alert_id: UUID,
        action: AuditAction,
        actor_id: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        is_mock: bool = False,
    ) -> AlertAuditLog:
        """
        Log an action on an alert.

        Args:
            alert_id: The alert being acted upon
            action: The type of action being performed
            actor_id: UUID of the staff/admin performing the action (None for system)
            actor_type: Type of actor (admin, staff, system)
            details: Additional details about the action
            ip_address: IP address of the request
            user_agent: User agent string
            is_mock: Whether this is a demo/mock action

        Returns:
            The created audit log entry
        """
        audit_log = AlertAuditLog(
            alert_id=alert_id,
            action=action,
            actor_id=actor_id,
            actor_type=actor_type,
            details=details or {},
            ip_address=ip_address,
            user_agent=user_agent,
            is_mock=is_mock,
            timestamp=datetime.utcnow(),
        )

        self.db.add(audit_log)
        self.db.flush()

        logger.info(
            f"Audit log created: alert={alert_id}, action={action.value}, "
            f"actor={actor_id}, actor_type={actor_type.value}"
        )

        return audit_log

    def log_alert_created(
        self,
        alert_id: UUID,
        created_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        details: Optional[Dict[str, Any]] = None,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log alert creation"""
        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.CREATED,
            actor_id=created_by,
            actor_type=actor_type,
            details=details,
            is_mock=is_mock,
            **kwargs
        )

    def log_alert_assigned(
        self,
        alert_id: UUID,
        assigned_to: UUID,
        assigned_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        reason: str = "auto",
        proximity_score: Optional[float] = None,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log alert assignment"""
        details = {
            "assigned_to": str(assigned_to),
            "reason": reason,
        }
        if proximity_score is not None:
            details["proximity_score"] = proximity_score

        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.ASSIGNED,
            actor_id=assigned_by,
            actor_type=actor_type,
            details=details,
            is_mock=is_mock,
            **kwargs
        )

    def log_alert_acknowledged(
        self,
        alert_id: UUID,
        acknowledged_by: UUID,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log alert acknowledgment"""
        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.ACKNOWLEDGED,
            actor_id=acknowledged_by,
            actor_type=ActorType.STAFF,
            is_mock=is_mock,
            **kwargs
        )

    def log_status_change(
        self,
        alert_id: UUID,
        previous_status: str,
        new_status: str,
        changed_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.STAFF,
        notes: Optional[str] = None,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log status change"""
        details = {
            "previous_status": previous_status,
            "new_status": new_status,
        }
        if notes:
            details["notes"] = notes

        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.STATUS_CHANGED,
            actor_id=changed_by,
            actor_type=actor_type,
            details=details,
            is_mock=is_mock,
            **kwargs
        )

    def log_note_added(
        self,
        alert_id: UUID,
        note: str,
        added_by: UUID,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log note addition"""
        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.NOTE_ADDED,
            actor_id=added_by,
            actor_type=ActorType.STAFF,
            details={"note": note},
            is_mock=is_mock,
            **kwargs
        )

    def log_alert_resolved(
        self,
        alert_id: UUID,
        resolved_by: UUID,
        resolution_type: str,
        resolution_notes: str,
        actor_type: ActorType = ActorType.STAFF,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log alert resolution"""
        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.RESOLVED,
            actor_id=resolved_by,
            actor_type=actor_type,
            details={
                "resolution_type": resolution_type,
                "resolution_notes": resolution_notes,
            },
            is_mock=is_mock,
            **kwargs
        )

    def log_alert_escalated(
        self,
        alert_id: UUID,
        escalated_to: UUID,
        reason: str,
        escalation_count: int,
        escalated_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.SYSTEM,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log alert escalation"""
        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.ESCALATED,
            actor_id=escalated_by,
            actor_type=actor_type,
            details={
                "escalated_to": str(escalated_to),
                "reason": reason,
                "escalation_count": escalation_count,
            },
            is_mock=is_mock,
            **kwargs
        )

    def log_alert_reassigned(
        self,
        alert_id: UUID,
        previous_assignee: UUID,
        new_assignee: UUID,
        reassigned_by: UUID,
        reason: str,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log alert reassignment"""
        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.REASSIGNED,
            actor_id=reassigned_by,
            actor_type=ActorType.ADMIN,
            details={
                "previous_assignee": str(previous_assignee),
                "new_assignee": str(new_assignee),
                "reason": reason,
            },
            is_mock=is_mock,
            **kwargs
        )

    def log_severity_change(
        self,
        alert_id: UUID,
        previous_severity: str,
        new_severity: str,
        changed_by: Optional[UUID] = None,
        actor_type: ActorType = ActorType.STAFF,
        reason: Optional[str] = None,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log severity change"""
        details = {
            "previous_severity": previous_severity,
            "new_severity": new_severity,
        }
        if reason:
            details["reason"] = reason

        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.SEVERITY_CHANGED,
            actor_id=changed_by,
            actor_type=actor_type,
            details=details,
            is_mock=is_mock,
            **kwargs
        )

    def log_backup_requested(
        self,
        alert_id: UUID,
        requested_by: UUID,
        backup_staff_id: UUID,
        is_mock: bool = False,
        **kwargs
    ) -> AlertAuditLog:
        """Log backup request"""
        return self.log_action(
            alert_id=alert_id,
            action=AuditAction.BACKUP_REQUESTED,
            actor_id=requested_by,
            actor_type=ActorType.STAFF,
            details={"backup_staff_id": str(backup_staff_id)},
            is_mock=is_mock,
            **kwargs
        )

    def get_alert_audit_trail(
        self,
        alert_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AlertAuditLog]:
        """
        Get the complete audit trail for an alert.

        Args:
            alert_id: The alert to get audit trail for
            limit: Maximum number of entries to return
            offset: Number of entries to skip

        Returns:
            List of audit log entries ordered by timestamp descending
        """
        return (
            self.db.query(AlertAuditLog)
            .filter(AlertAuditLog.alert_id == alert_id)
            .order_by(AlertAuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    def get_audit_count(self, alert_id: UUID) -> int:
        """Get total count of audit entries for an alert"""
        return (
            self.db.query(AlertAuditLog)
            .filter(AlertAuditLog.alert_id == alert_id)
            .count()
        )

    def get_actor_actions(
        self,
        actor_id: UUID,
        limit: int = 100,
        offset: int = 0,
    ) -> List[AlertAuditLog]:
        """Get all actions performed by a specific actor"""
        return (
            self.db.query(AlertAuditLog)
            .filter(AlertAuditLog.actor_id == actor_id)
            .order_by(AlertAuditLog.timestamp.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )
