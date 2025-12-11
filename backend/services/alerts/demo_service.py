"""
Demo Service for running interactive alert demonstrations.
Manages scenario execution, timeline progression, and state management.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from uuid import UUID
import threading
import time

from sqlalchemy.orm import Session

from models.db.alerts import (
    Alert,
    DemoScenario,
    DemoTimelineEvent,
    AlertSeverity,
    AlertStatus,
    ActorType,
    StaffProfile,
)
from models.schemas.alerts import AlertCreate, AlertStatusEnum, ResolutionTypeEnum
from .alert_service import AlertService
from .staff_service import StaffService
from .notification_service import NotificationService
from .assignment_engine import AssignmentEngine
from .audit_service import AuditService

logger = logging.getLogger(__name__)


class DemoState:
    """Holds the current state of a running demo"""

    def __init__(self):
        self.scenario_id: Optional[str] = None
        self.scenario_name: Optional[str] = None
        self.alert_id: Optional[UUID] = None
        self.current_step: int = 0
        self.total_steps: int = 0
        self.started_at: Optional[datetime] = None
        self.paused: bool = False
        self.speed: float = 1.0
        self.auto_advance: bool = True
        # Store event data as dicts to avoid SQLAlchemy session issues
        self.timeline_events: List[Dict[str, Any]] = []
        self._advance_timer: Optional[threading.Timer] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for API response"""
        elapsed = 0
        if self.started_at and not self.paused:
            elapsed = (datetime.utcnow() - self.started_at).total_seconds() * self.speed

        current_event = None
        next_event = None
        if self.timeline_events:
            if 0 < self.current_step <= len(self.timeline_events):
                current_event = self.timeline_events[self.current_step - 1]
            if self.current_step < len(self.timeline_events):
                next_event = self.timeline_events[self.current_step]

        return {
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "alert_id": str(self.alert_id) if self.alert_id else None,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "current_status": current_event["action"] if current_event else None,
            "elapsed_seconds": elapsed,
            "speed": self.speed,
            "paused": self.paused,
            "auto_advance": self.auto_advance,
            "next_step_description": next_event["description"] if next_event else None,
            "next_step_in_seconds": (
                (next_event["delay_seconds"] - elapsed) / self.speed
                if next_event and not self.paused else None
            ),
        }

    def reset(self):
        """Reset the demo state"""
        if self._advance_timer:
            self._advance_timer.cancel()
        self.__init__()


# Global demo state (in production, use Redis or database)
_demo_state = DemoState()
_demo_lock = threading.Lock()


class DemoService:
    """
    Service for managing interactive alert demonstrations.

    Features:
    - Start/stop demo scenarios
    - Auto-advance timeline events
    - Manual step control
    - Speed adjustment
    - Pause/resume functionality
    """

    def __init__(self, db: Session):
        self.db = db
        self.alert_service = AlertService(db)
        self.staff_service = StaffService(db)
        self.notification_service = NotificationService(db)
        self.assignment_engine = AssignmentEngine(db)
        self.audit_service = AuditService(db)

    def get_scenarios(self, active_only: bool = True) -> List[DemoScenario]:
        """Get all available demo scenarios"""
        query = self.db.query(DemoScenario)
        if active_only:
            query = query.filter(DemoScenario.is_active == True)
        return query.order_by(DemoScenario.display_order).all()

    def get_scenario(self, scenario_id: str) -> Optional[DemoScenario]:
        """Get a specific scenario by ID"""
        return self.db.query(DemoScenario).filter(DemoScenario.id == scenario_id).first()

    def get_state(self) -> Dict[str, Any]:
        """Get current demo state"""
        with _demo_lock:
            return _demo_state.to_dict()

    def start_scenario(
        self,
        scenario_id: str,
        speed: float = 1.0,
        auto_advance: bool = True,
    ) -> Dict[str, Any]:
        """
        Start a demo scenario.

        Args:
            scenario_id: ID of the scenario to run
            speed: Playback speed multiplier (1.0 = real time)
            auto_advance: Whether to auto-advance through timeline

        Returns:
            Initial demo state
        """
        global _demo_state

        scenario = self.get_scenario(scenario_id)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_id}' not found")

        # Stop any existing demo
        self.stop_demo()

        with _demo_lock:
            # Initialize state
            _demo_state.scenario_id = scenario.id
            _demo_state.scenario_name = scenario.name
            _demo_state.speed = speed or scenario.default_speed
            _demo_state.auto_advance = auto_advance if auto_advance is not None else scenario.auto_advance
            # Convert ORM objects to dicts to avoid session issues in background threads
            _demo_state.timeline_events = [
                {
                    "step_number": e.step_number,
                    "delay_seconds": e.delay_seconds,
                    "action": e.action,
                    "description": e.description,
                    "narration_text": e.narration_text,
                    "action_data": e.action_data or {},
                }
                for e in sorted(scenario.timeline_events, key=lambda x: x.step_number)
            ]
            _demo_state.total_steps = len(_demo_state.timeline_events)
            _demo_state.current_step = 0
            _demo_state.started_at = datetime.utcnow()
            _demo_state.paused = False

            # Create the alert from template
            alert = self._create_demo_alert(scenario)
            _demo_state.alert_id = alert.id

            # Execute first step (create)
            self._execute_step(0)

            # Schedule next step if auto-advance
            if _demo_state.auto_advance and _demo_state.total_steps > 1:
                self._schedule_next_step()

            logger.info(f"Started demo scenario: {scenario.name}")
            return _demo_state.to_dict()

    def stop_demo(self) -> Dict[str, Any]:
        """Stop the current demo"""
        global _demo_state

        with _demo_lock:
            if _demo_state._advance_timer:
                _demo_state._advance_timer.cancel()

            # Clean up the demo alert if it exists
            if _demo_state.alert_id:
                alert = self.alert_service.get_alert(_demo_state.alert_id)
                if alert and alert.status != AlertStatus.RESOLVED:
                    # Mark as resolved
                    self.alert_service.resolve_alert(
                        alert_id=_demo_state.alert_id,
                        resolved_by=None,
                        resolution_type=ResolutionTypeEnum.NO_ACTION_REQUIRED,
                        resolution_notes="Demo stopped",
                    )

            result = _demo_state.to_dict()
            _demo_state.reset()
            logger.info("Demo stopped")
            return result

    def pause_demo(self) -> Dict[str, Any]:
        """Pause the current demo"""
        global _demo_state

        with _demo_lock:
            if _demo_state._advance_timer:
                _demo_state._advance_timer.cancel()
            _demo_state.paused = True
            logger.info("Demo paused")
            return _demo_state.to_dict()

    def resume_demo(self) -> Dict[str, Any]:
        """Resume a paused demo"""
        global _demo_state

        with _demo_lock:
            if not _demo_state.scenario_id:
                raise ValueError("No demo to resume")

            _demo_state.paused = False

            if _demo_state.auto_advance:
                self._schedule_next_step()

            logger.info("Demo resumed")
            return _demo_state.to_dict()

    def advance_step(self) -> Dict[str, Any]:
        """Manually advance to the next step"""
        global _demo_state

        with _demo_lock:
            if not _demo_state.scenario_id:
                raise ValueError("No demo running")

            if _demo_state.current_step >= _demo_state.total_steps:
                raise ValueError("Demo complete - no more steps")

            # Cancel auto-advance timer
            if _demo_state._advance_timer:
                _demo_state._advance_timer.cancel()

            # Execute next step
            self._execute_step(_demo_state.current_step)

            # Reschedule if auto-advance
            if _demo_state.auto_advance and not _demo_state.paused:
                self._schedule_next_step()

            return _demo_state.to_dict()

    def set_speed(self, speed: float) -> Dict[str, Any]:
        """Set the playback speed"""
        global _demo_state

        if speed < 0.1 or speed > 100:
            raise ValueError("Speed must be between 0.1 and 100")

        with _demo_lock:
            _demo_state.speed = speed

            # Reschedule next step with new timing
            if _demo_state.auto_advance and not _demo_state.paused:
                if _demo_state._advance_timer:
                    _demo_state._advance_timer.cancel()
                self._schedule_next_step()

            logger.info(f"Demo speed set to {speed}x")
            return _demo_state.to_dict()

    def _create_demo_alert(self, scenario: DemoScenario) -> Alert:
        """Create an alert from scenario template"""
        template = scenario.alert_template

        alert_data = AlertCreate(
            title=template.get("title", scenario.name),
            description=template.get("description", scenario.description),
            severity=scenario.severity.value,
            location=template.get("location", {"zone_id": "DEMO"}),
            anomaly_type=scenario.id,
            affected_entities=template.get("affected_entities", []),
            data_sources=template.get("data_sources", []),
            evidence=template.get("evidence", {}),
            is_mock=True,
            mock_scenario=scenario.id,
        )

        alert = self.alert_service.create_alert(
            alert_data=alert_data,
            actor_type=ActorType.SYSTEM,
        )

        return alert

    def _execute_step(self, step_index: int):
        """Execute a specific timeline step"""
        global _demo_state

        if step_index >= len(_demo_state.timeline_events):
            logger.info("Demo complete - all steps executed")
            return

        event = _demo_state.timeline_events[step_index]
        _demo_state.current_step = step_index + 1

        logger.info(f"Executing demo step {_demo_state.current_step}: {event['action']} - {event['description']}")

        try:
            self._execute_action(event)
        except Exception as e:
            logger.error(f"Error executing demo step: {e}")

    def _execute_action(self, event: Dict[str, Any]):
        """Execute the action for a timeline event"""
        action = event["action"]
        data = event.get("action_data") or {}
        alert_id = _demo_state.alert_id

        if action == "create":
            # Alert already created, just log
            pass

        elif action == "assign":
            staff_name = data.get("staff_name")
            staff = self._get_staff_by_name(staff_name)
            if staff:
                self.alert_service.assign_alert(
                    alert_id=alert_id,
                    staff_id=staff.id,
                    actor_type=ActorType.SYSTEM,
                    reason="demo_assignment",
                )
                # Queue notification
                alert = self.alert_service.get_alert(alert_id)
                self.notification_service.notify_staff_of_assignment(staff, alert)

        elif action == "multi_assign":
            staff_names = data.get("staff_names", [])
            alert = self.alert_service.get_alert(alert_id)
            for i, name in enumerate(staff_names):
                staff = self._get_staff_by_name(name)
                if staff:
                    if i == 0:
                        self.alert_service.assign_alert(
                            alert_id=alert_id,
                            staff_id=staff.id,
                            actor_type=ActorType.SYSTEM,
                            reason="demo_critical_primary",
                        )
                    self.notification_service.notify_staff_of_assignment(staff, alert, is_critical=True)

        elif action == "acknowledge":
            alert = self.alert_service.get_alert(alert_id)
            if alert and alert.assigned_to:
                self.alert_service.acknowledge_alert(
                    alert_id=alert_id,
                    staff_id=alert.assigned_to,
                )

        elif action == "status_change":
            new_status = data.get("new_status", "investigating")
            note = data.get("note")
            alert = self.alert_service.get_alert(alert_id)
            if alert:
                self.alert_service.update_status(
                    alert_id=alert_id,
                    new_status=AlertStatusEnum(new_status),
                    updated_by=alert.assigned_to,
                    actor_type=ActorType.STAFF,
                    notes=note,
                )

        elif action == "note_add":
            note = data.get("note", event["description"])
            alert = self.alert_service.get_alert(alert_id)
            if alert and alert.assigned_to:
                self.alert_service.add_note(
                    alert_id=alert_id,
                    note=note,
                    added_by=alert.assigned_to,
                )

        elif action == "backup_request":
            staff_name = data.get("staff_name")
            staff = self._get_staff_by_name(staff_name)
            alert = self.alert_service.get_alert(alert_id)
            if staff and alert:
                self.notification_service.notify_staff_of_assignment(staff, alert, is_critical=True)

        elif action == "escalate":
            reason = data.get("reason", "Demo escalation")
            new_assignee_name = data.get("new_assignee")
            new_staff = self._get_staff_by_name(new_assignee_name) if new_assignee_name else None

            if new_staff:
                self.alert_service.escalate_alert(
                    alert_id=alert_id,
                    escalate_to=new_staff.id,
                    reason=reason,
                    actor_type=ActorType.SYSTEM,
                )

        elif action == "severity_change":
            new_severity = data.get("new_severity", "high")
            from models.schemas.alerts import AlertUpdate, AlertSeverityEnum
            self.alert_service.update_alert(
                alert_id=alert_id,
                update_data=AlertUpdate(severity=AlertSeverityEnum(new_severity)),
                actor_type=ActorType.SYSTEM,
            )

        elif action == "resolve":
            resolution_type_str = data.get("resolution_type", "resolved")
            notes = data.get("notes", "Demo resolution")
            alert = self.alert_service.get_alert(alert_id)
            self.alert_service.resolve_alert(
                alert_id=alert_id,
                resolved_by=alert.assigned_to if alert else None,
                resolution_type=ResolutionTypeEnum(resolution_type_str),
                resolution_notes=notes,
            )

        # Process any queued notifications
        self.notification_service.process_queue(batch_size=10)

    def _schedule_next_step(self):
        """Schedule the next auto-advance step"""
        global _demo_state

        if _demo_state.current_step >= _demo_state.total_steps:
            return

        next_event = _demo_state.timeline_events[_demo_state.current_step]

        # Calculate delay based on speed
        if _demo_state.current_step == 0:
            delay = next_event["delay_seconds"] / _demo_state.speed
        else:
            prev_event = _demo_state.timeline_events[_demo_state.current_step - 1]
            delay = (next_event["delay_seconds"] - prev_event["delay_seconds"]) / _demo_state.speed

        delay = max(0.1, delay)  # Minimum delay

        def advance():
            with _demo_lock:
                if not _demo_state.paused and _demo_state.scenario_id:
                    self._execute_step(_demo_state.current_step)
                    if _demo_state.current_step < _demo_state.total_steps:
                        self._schedule_next_step()

        _demo_state._advance_timer = threading.Timer(delay, advance)
        _demo_state._advance_timer.start()

    def _get_staff_by_name(self, name: str) -> Optional[StaffProfile]:
        """Get staff by name (for demo purposes)"""
        if not name:
            return None
        return self.db.query(StaffProfile).filter(StaffProfile.name == name).first()

    def get_scenario_details(self, scenario_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a scenario"""
        scenario = self.get_scenario(scenario_id)
        if not scenario:
            return None

        return {
            "id": scenario.id,
            "name": scenario.name,
            "description": scenario.description,
            "severity": scenario.severity.value,
            "duration_seconds": scenario.duration_seconds,
            "auto_advance": scenario.auto_advance,
            "default_speed": scenario.default_speed,
            "alert_template": scenario.alert_template,
            "timeline": [
                {
                    "step": e.step_number,
                    "delay_seconds": e.delay_seconds,
                    "action": e.action,
                    "description": e.description,
                    "narration": e.narration_text,
                }
                for e in sorted(scenario.timeline_events, key=lambda x: x.step_number)
            ],
        }
