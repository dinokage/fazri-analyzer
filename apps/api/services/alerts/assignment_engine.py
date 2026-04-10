"""
Assignment Engine for automatically assigning alerts to staff.
Implements proximity-based assignment with workload balancing and skill matching.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from uuid import UUID
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, desc

from models.db.alerts import (
    Alert,
    AlertAssignment,
    AlertStatus,
    AlertSeverity,
    StaffProfile,
    StaffLocation,
    StaffRole,
    ActorType,
)
from .staff_service import StaffService
from .alert_service import AlertService
from .audit_service import AuditService
from .notification_service import NotificationService
from config import settings

logger = logging.getLogger(__name__)


# Zone adjacency map - defines which zones are adjacent and their distances
# This can be loaded from Neo4j or configured statically
ZONE_ADJACENCY = {
    "LIB_ENT": ["CAF_01", "ADMIN_LOBBY", "AUDITORIUM"],
    "LAB_101": ["LAB_102", "LAB_305", "ADMIN_LOBBY"],
    "LAB_102": ["LAB_101", "LAB_305"],
    "LAB_305": ["LAB_101", "LAB_102"],
    "CAF_01": ["LIB_ENT", "GYM", "AUDITORIUM"],
    "GYM": ["CAF_01", "HOSTEL_GATE"],
    "HOSTEL_GATE": ["GYM", "ADMIN_LOBBY"],
    "ADMIN_LOBBY": ["LIB_ENT", "LAB_101", "HOSTEL_GATE", "SEM_01"],
    "AUDITORIUM": ["LIB_ENT", "CAF_01", "SEM_01"],
    "SEM_01": ["ADMIN_LOBBY", "AUDITORIUM", "ROOM_A1"],
    "ROOM_A1": ["ROOM_A2", "SEM_01"],
    "ROOM_A2": ["ROOM_A1"],
}

# Role-based skill matching for alert types
ROLE_SKILL_MATCH = {
    # Alert anomaly type -> preferred roles (in order of preference)
    "unauthorized_access": [StaffRole.SECURITY, StaffRole.SUPERVISOR, StaffRole.ADMIN],
    "suspicious_loitering": [StaffRole.SECURITY, StaffRole.SUPERVISOR],
    "off_hours_access": [StaffRole.SECURITY, StaffRole.LAB_SUPERVISOR],
    "role_violation": [StaffRole.SUPERVISOR, StaffRole.SECURITY],
    "impossible_travel": [StaffRole.SUPERVISOR, StaffRole.ADMIN],
    "curfew_violation": [StaffRole.SECURITY, StaffRole.SUPERVISOR],
    "overcrowding": [StaffRole.SECURITY, StaffRole.SUPERVISOR],
    "equipment_misuse": [StaffRole.LAB_SUPERVISOR, StaffRole.SUPERVISOR],
    "entry_without_exit": [StaffRole.SECURITY],
    "exit_without_entry": [StaffRole.SECURITY],
    # Default for unknown types
    "default": [StaffRole.SECURITY, StaffRole.SUPERVISOR, StaffRole.ADMIN],
}


class AssignmentEngine:
    """
    Engine for automatically assigning alerts to the most appropriate staff.

    Assignment is based on:
    1. Proximity - Distance from staff to alert location
    2. Workload - Current number of active assignments
    3. Skill Match - Role appropriateness for alert type
    """

    def __init__(self, db: Session, neo4j_driver=None):
        self.db = db
        self.neo4j_driver = neo4j_driver
        self.staff_service = StaffService(db)
        self.alert_service = AlertService(db)
        self.audit_service = AuditService(db)
        self.notification_service = NotificationService(db)

    def assign_alert(
        self,
        alert: Alert,
        exclude_staff_ids: Optional[List[UUID]] = None,
        force_staff_id: Optional[UUID] = None,
    ) -> Optional[StaffProfile]:
        """
        Automatically assign an alert to the best available staff member.

        Args:
            alert: The alert to assign
            exclude_staff_ids: Staff IDs to exclude from consideration
            force_staff_id: Force assignment to specific staff (for manual override)

        Returns:
            The assigned staff member, or None if no one available
        """
        if force_staff_id:
            staff = self.staff_service.get_staff(force_staff_id)
            if staff:
                self._do_assignment(alert, staff, reason="manual")
                return staff
            return None

        # Get alert location
        zone_id = alert.location.get("zone_id") if alert.location else None
        if not zone_id:
            logger.warning(f"Alert {alert.id} has no zone_id, cannot auto-assign")
            return None

        # Get candidate staff members
        candidates = self._get_candidates(
            zone_id=zone_id,
            alert_type=alert.anomaly_type,
            severity=alert.severity,
            exclude_ids=exclude_staff_ids or [],
        )

        if not candidates:
            logger.warning(f"No available staff for alert {alert.id}")
            return None

        # Score and rank candidates
        scored_candidates = self._score_candidates(
            candidates=candidates,
            zone_id=zone_id,
            alert_type=alert.anomaly_type,
            severity=alert.severity,
        )

        # Select best candidate (lowest score)
        best_candidate, score, details = scored_candidates[0]

        # Perform assignment
        self._do_assignment(
            alert=alert,
            staff=best_candidate,
            reason="auto",
            proximity_score=details.get("proximity_score"),
        )

        logger.info(
            f"Auto-assigned alert {alert.id} to {best_candidate.name} "
            f"(score={score:.2f}, zone={zone_id})"
        )

        return best_candidate

    def assign_critical_alert(
        self,
        alert: Alert,
        max_assignees: int = 3,
    ) -> List[StaffProfile]:
        """
        Assign a critical alert to multiple staff members.

        For critical alerts, we notify multiple staff to ensure quick response.

        Args:
            alert: The critical alert
            max_assignees: Maximum number of staff to assign

        Returns:
            List of assigned staff members
        """
        zone_id = alert.location.get("zone_id") if alert.location else None
        if not zone_id:
            return []

        # Get all available staff
        candidates = self._get_candidates(
            zone_id=zone_id,
            alert_type=alert.anomaly_type,
            severity=alert.severity,
            exclude_ids=[],
        )

        if not candidates:
            return []

        # Score candidates
        scored_candidates = self._score_candidates(
            candidates=candidates,
            zone_id=zone_id,
            alert_type=alert.anomaly_type,
            severity=alert.severity,
        )

        # Select top N candidates
        assigned_staff = []
        for i, (staff, score, details) in enumerate(scored_candidates[:max_assignees]):
            if i == 0:
                # Primary assignee
                self._do_assignment(
                    alert=alert,
                    staff=staff,
                    reason="critical_primary",
                    proximity_score=details.get("proximity_score"),
                )
            else:
                # Additional assignees - create assignment records but don't change alert.assigned_to
                assignment = AlertAssignment(
                    alert_id=alert.id,
                    staff_id=staff.id,
                    assignment_reason="critical_backup",
                    proximity_score=details.get("proximity_score"),
                    is_active=True,
                )
                self.db.add(assignment)

                # Send notifications to backup staff as well
                self.notification_service.notify_staff_of_assignment(
                    staff=staff,
                    alert=alert,
                    is_critical=True,
                )

            assigned_staff.append(staff)

        self.db.commit()

        logger.info(
            f"Critical alert {alert.id} assigned to {len(assigned_staff)} staff: "
            f"{[s.name for s in assigned_staff]}"
        )

        return assigned_staff

    def find_escalation_target(
        self,
        alert: Alert,
        current_assignee: Optional[UUID] = None,
    ) -> Optional[StaffProfile]:
        """
        Find an appropriate escalation target for an alert.

        Escalation hierarchy:
        1. If current assignee is security -> escalate to supervisor
        2. If current assignee is supervisor -> escalate to admin
        3. If no current assignee -> assign to supervisor

        Args:
            alert: The alert to escalate
            current_assignee: Current staff assigned (to exclude)

        Returns:
            The escalation target, or None if no one available
        """
        exclude_ids = [current_assignee] if current_assignee else []

        # Determine target role based on current assignee
        target_roles = [StaffRole.SUPERVISOR, StaffRole.ADMIN]

        if current_assignee:
            current_staff = self.staff_service.get_staff(current_assignee)
            if current_staff:
                if current_staff.role == StaffRole.SECURITY:
                    target_roles = [StaffRole.SUPERVISOR, StaffRole.ADMIN]
                elif current_staff.role == StaffRole.SUPERVISOR:
                    target_roles = [StaffRole.ADMIN]
                elif current_staff.role == StaffRole.LAB_SUPERVISOR:
                    target_roles = [StaffRole.SUPERVISOR, StaffRole.ADMIN]

        # Find available staff with target roles
        for role in target_roles:
            available = self.staff_service.get_available_staff(
                role=role,
                exclude_ids=exclude_ids,
            )
            if available:
                # Return the first available (they're already filtered by availability)
                return available[0]

        # Last resort - any available staff
        all_available = self.staff_service.get_available_staff(exclude_ids=exclude_ids)
        return all_available[0] if all_available else None

    def _get_candidates(
        self,
        zone_id: str,
        alert_type: Optional[str],
        severity: AlertSeverity,
        exclude_ids: List[UUID],
    ) -> List[Tuple[StaffProfile, str, int]]:
        """
        Get candidate staff members for assignment.

        Returns list of (staff, current_zone, zone_distance) tuples.
        """
        # Get adjacent zones
        adjacent_zones = self._get_adjacent_zones(zone_id, max_distance=3)

        # Get staff in or near the zone
        candidates = self.staff_service.get_nearby_staff(
            zone_id=zone_id,
            adjacent_zones=adjacent_zones,
            exclude_ids=exclude_ids,
            on_duty_only=True,
        )

        # Filter by availability (not at max capacity)
        available_candidates = []
        for staff, current_zone, distance in candidates:
            if self.staff_service.is_available_for_assignment(staff.id):
                available_candidates.append((staff, current_zone, distance))

        return available_candidates

    def _score_candidates(
        self,
        candidates: List[Tuple[StaffProfile, str, int]],
        zone_id: str,
        alert_type: Optional[str],
        severity: AlertSeverity,
    ) -> List[Tuple[StaffProfile, float, Dict[str, Any]]]:
        """
        Score and rank candidates for assignment.

        Lower score = better candidate.

        Score = (proximity_weight * proximity_score) +
                (workload_weight * workload_score) +
                (skill_weight * skill_score)
        """
        scored = []

        for staff, current_zone, zone_distance in candidates:
            # Calculate individual scores (0-1, lower is better)
            proximity_score = self._calculate_proximity_score(zone_distance)
            workload_score = self._calculate_workload_score(staff)
            skill_score = self._calculate_skill_score(staff, alert_type)

            # Calculate weighted total
            total_score = (
                settings.ALERT_WEIGHT_PROXIMITY * proximity_score +
                settings.ALERT_WEIGHT_WORKLOAD * workload_score +
                settings.ALERT_WEIGHT_SKILL_MATCH * skill_score
            )

            # Severity bonus - reduce score for supervisors/admins on critical alerts
            if severity == AlertSeverity.CRITICAL:
                if staff.role in [StaffRole.SUPERVISOR, StaffRole.ADMIN]:
                    total_score *= 0.8  # 20% bonus

            details = {
                "proximity_score": proximity_score,
                "workload_score": workload_score,
                "skill_score": skill_score,
                "current_zone": current_zone,
                "zone_distance": zone_distance,
            }

            scored.append((staff, total_score, details))

        # Sort by score (ascending - lower is better)
        scored.sort(key=lambda x: x[1])

        return scored

    def _calculate_proximity_score(self, zone_distance: int) -> float:
        """
        Calculate proximity score (0-1, lower is better).

        Distance 0 (same zone) = 0.0
        Distance 1 (adjacent) = 0.33
        Distance 2 = 0.67
        Distance 3+ = 1.0
        """
        if zone_distance == 0:
            return 0.0
        elif zone_distance == 1:
            return 0.33
        elif zone_distance == 2:
            return 0.67
        else:
            return 1.0

    def _calculate_workload_score(self, staff: StaffProfile) -> float:
        """
        Calculate workload score (0-1, lower is better).

        Based on current assignments relative to max capacity.
        """
        current = self.staff_service.get_active_assignment_count(staff.id)
        max_assignments = staff.max_concurrent_assignments

        if max_assignments == 0:
            return 1.0

        return min(current / max_assignments, 1.0)

    def _calculate_skill_score(
        self,
        staff: StaffProfile,
        alert_type: Optional[str],
    ) -> float:
        """
        Calculate skill match score (0-1, lower is better).

        Based on role appropriateness for alert type.
        """
        if not alert_type:
            alert_type = "default"

        preferred_roles = ROLE_SKILL_MATCH.get(alert_type, ROLE_SKILL_MATCH["default"])

        try:
            # Position in preference list (0 = best match)
            position = preferred_roles.index(staff.role)
            # Normalize to 0-1
            return position / len(preferred_roles)
        except ValueError:
            # Role not in preferred list
            return 1.0

    def _get_adjacent_zones(self, zone_id: str, max_distance: int = 3) -> List[str]:
        """
        Get zones adjacent to the given zone, ordered by distance.

        Uses BFS to find zones up to max_distance away.
        """
        if self.neo4j_driver:
            return self._get_adjacent_zones_from_neo4j(zone_id, max_distance)

        # Fall back to static map
        return self._get_adjacent_zones_static(zone_id, max_distance)

    def _get_adjacent_zones_static(self, zone_id: str, max_distance: int) -> List[str]:
        """Get adjacent zones from static map using BFS"""
        if zone_id not in ZONE_ADJACENCY:
            return []

        visited = {zone_id}
        result = []
        current_level = [zone_id]

        for distance in range(1, max_distance + 1):
            next_level = []
            for zone in current_level:
                for adjacent in ZONE_ADJACENCY.get(zone, []):
                    if adjacent not in visited:
                        visited.add(adjacent)
                        next_level.append(adjacent)
                        result.append(adjacent)
            current_level = next_level
            if not current_level:
                break

        return result

    def _get_adjacent_zones_from_neo4j(self, zone_id: str, max_distance: int) -> List[str]:
        """Get adjacent zones from Neo4j graph"""
        try:
            with self.neo4j_driver.session() as session:
                # Use variable-length path to find zones within max_distance
                result = session.run("""
                    MATCH path = (start:Zone {zone_id: $zone_id})-[:CONNECTED_TO*1..3]-(end:Zone)
                    WHERE start <> end
                    WITH end, length(path) as distance
                    ORDER BY distance
                    RETURN DISTINCT end.zone_id as zone_id, min(distance) as distance
                    ORDER BY distance
                """, zone_id=zone_id, max_distance=max_distance)

                return [record["zone_id"] for record in result]
        except Exception as e:
            logger.error(f"Error getting adjacent zones from Neo4j: {e}")
            return self._get_adjacent_zones_static(zone_id, max_distance)

    def _do_assignment(
        self,
        alert: Alert,
        staff: StaffProfile,
        reason: str,
        proximity_score: Optional[float] = None,
        send_notification: bool = True,
    ):
        """Perform the actual assignment and send notifications"""
        self.alert_service.assign_alert(
            alert_id=alert.id,
            staff_id=staff.id,
            actor_type=ActorType.SYSTEM,
            reason=reason,
            proximity_score=proximity_score,
        )

        # Send notifications if enabled
        if send_notification:
            is_critical = alert.severity == AlertSeverity.CRITICAL
            self.notification_service.notify_staff_of_assignment(
                staff=staff,
                alert=alert,
                is_critical=is_critical,
            )
            logger.info(f"Notifications queued for {staff.name} regarding alert {alert.id}")


class EscalationChecker:
    """
    Background task to check for alerts that need escalation.

    Escalation triggers:
    1. No acknowledgment within ALERT_ESCALATION_NO_ACK_MINUTES
    2. No resolution within ALERT_ESCALATION_NO_RESOLUTION_MINUTES
    """

    def __init__(self, db: Session):
        self.db = db
        self.assignment_engine = AssignmentEngine(db)
        self.alert_service = AlertService(db)

    def check_and_escalate(self) -> Dict[str, int]:
        """
        Check all active alerts and escalate if needed.

        Returns:
            Dict with counts of escalations performed
        """
        now = datetime.utcnow()
        escalated_counts = {
            "no_acknowledgment": 0,
            "no_resolution": 0,
            "max_reached": 0,
        }

        # Find alerts needing escalation due to no acknowledgment
        ack_threshold = now - timedelta(minutes=settings.ALERT_ESCALATION_NO_ACK_MINUTES)
        unacked_alerts = (
            self.db.query(Alert)
            .filter(
                Alert.status == AlertStatus.ASSIGNED,
                Alert.assigned_at < ack_threshold,
                Alert.acknowledged_at.is_(None),
                Alert.escalation_count < settings.ALERT_MAX_ESCALATIONS,
                Alert.is_mock == False,
            )
            .all()
        )

        for alert in unacked_alerts:
            escalated = self._escalate_alert(
                alert,
                reason=f"No acknowledgment after {settings.ALERT_ESCALATION_NO_ACK_MINUTES} minutes",
            )
            if escalated:
                escalated_counts["no_acknowledgment"] += 1

        # Find alerts needing escalation due to no resolution
        resolution_threshold = now - timedelta(minutes=settings.ALERT_ESCALATION_NO_RESOLUTION_MINUTES)
        unresolved_alerts = (
            self.db.query(Alert)
            .filter(
                Alert.status.in_([AlertStatus.ACKNOWLEDGED, AlertStatus.INVESTIGATING]),
                Alert.acknowledged_at < resolution_threshold,
                Alert.escalation_count < settings.ALERT_MAX_ESCALATIONS,
                Alert.is_mock == False,
            )
            .all()
        )

        for alert in unresolved_alerts:
            escalated = self._escalate_alert(
                alert,
                reason=f"No resolution after {settings.ALERT_ESCALATION_NO_RESOLUTION_MINUTES} minutes",
            )
            if escalated:
                escalated_counts["no_resolution"] += 1

        # Log alerts that have reached max escalations
        max_escalated = (
            self.db.query(Alert)
            .filter(
                Alert.status != AlertStatus.RESOLVED,
                Alert.escalation_count >= settings.ALERT_MAX_ESCALATIONS,
                Alert.is_mock == False,
            )
            .count()
        )
        escalated_counts["max_reached"] = max_escalated

        logger.info(f"Escalation check complete: {escalated_counts}")

        return escalated_counts

    def _escalate_alert(self, alert: Alert, reason: str) -> bool:
        """
        Escalate a single alert.

        Returns True if escalation was successful.
        """
        # Find escalation target
        target = self.assignment_engine.find_escalation_target(
            alert=alert,
            current_assignee=alert.assigned_to,
        )

        if not target:
            logger.warning(f"No escalation target found for alert {alert.id}")
            return False

        # Perform escalation
        self.alert_service.escalate_alert(
            alert_id=alert.id,
            escalate_to=target.id,
            reason=reason,
        )

        logger.info(f"Escalated alert {alert.id} to {target.name}: {reason}")

        return True


def run_escalation_check(db: Session) -> Dict[str, int]:
    """
    Run the escalation check.

    This function can be called by a background scheduler (e.g., Celery beat, APScheduler).
    """
    checker = EscalationChecker(db)
    return checker.check_and_escalate()
