"""
Staff Service for managing security staff profiles and locations.
Handles staff CRUD operations, location tracking, and availability.
"""

import logging
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, func

from models.db.alerts import (
    StaffProfile,
    StaffLocation,
    StaffRole,
    Alert,
    AlertStatus,
)
from models.schemas.alerts import (
    StaffProfileCreate,
    StaffProfileUpdate,
    StaffLocationUpdate,
    StaffRoleEnum,
)
from config import settings

logger = logging.getLogger(__name__)


class StaffService:
    """Service for managing security staff"""

    def __init__(self, db: Session):
        self.db = db

    # =========================================================================
    # STAFF PROFILE CRUD
    # =========================================================================

    def create_staff(self, staff_data: StaffProfileCreate) -> StaffProfile:
        """
        Create a new staff profile.

        Args:
            staff_data: Staff creation data

        Returns:
            The created staff profile
        """
        staff = StaffProfile(
            entity_id=staff_data.entity_id,
            name=staff_data.name,
            email=staff_data.email,
            phone=staff_data.phone,
            role=StaffRole(staff_data.role.value),
            department=staff_data.department,
            on_duty=staff_data.on_duty,
            max_concurrent_assignments=staff_data.max_concurrent_assignments,
            contact_preferences=staff_data.contact_preferences.model_dump(),
            is_mock_user=staff_data.is_mock_user,
        )

        self.db.add(staff)
        self.db.commit()
        self.db.refresh(staff)

        logger.info(f"Staff created: id={staff.id}, name={staff.name}, role={staff.role.value}")

        return staff

    def get_staff(self, staff_id: UUID) -> Optional[StaffProfile]:
        """Get a staff profile by ID"""
        return self.db.query(StaffProfile).filter(StaffProfile.id == staff_id).first()

    def get_staff_by_email(self, email: str) -> Optional[StaffProfile]:
        """Get a staff profile by email"""
        return self.db.query(StaffProfile).filter(StaffProfile.email == email).first()

    def get_staff_by_entity_id(self, entity_id: str) -> Optional[StaffProfile]:
        """Get a staff profile by campus entity ID"""
        return self.db.query(StaffProfile).filter(StaffProfile.entity_id == entity_id).first()

    def get_all_staff(
        self,
        role: Optional[StaffRoleEnum] = None,
        on_duty: Optional[bool] = None,
        is_mock: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[List[StaffProfile], int]:
        """
        Get all staff with optional filters.

        Args:
            role: Filter by role
            on_duty: Filter by on-duty status
            is_mock: Filter by mock flag
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            Tuple of (staff list, total count)
        """
        query = self.db.query(StaffProfile)

        if role:
            query = query.filter(StaffProfile.role == StaffRole(role.value))

        if on_duty is not None:
            query = query.filter(StaffProfile.on_duty == on_duty)

        if is_mock is not None:
            query = query.filter(StaffProfile.is_mock_user == is_mock)

        total = query.count()

        staff = (
            query
            .order_by(StaffProfile.name)
            .offset(offset)
            .limit(limit)
            .all()
        )

        return staff, total

    def update_staff(
        self,
        staff_id: UUID,
        update_data: StaffProfileUpdate,
    ) -> Optional[StaffProfile]:
        """
        Update a staff profile.

        Args:
            staff_id: The staff to update
            update_data: The update data

        Returns:
            The updated staff or None if not found
        """
        staff = self.get_staff(staff_id)
        if not staff:
            return None

        if update_data.name is not None:
            staff.name = update_data.name

        if update_data.email is not None:
            staff.email = update_data.email

        if update_data.phone is not None:
            staff.phone = update_data.phone

        if update_data.role is not None:
            staff.role = StaffRole(update_data.role.value)

        if update_data.department is not None:
            staff.department = update_data.department

        if update_data.on_duty is not None:
            staff.on_duty = update_data.on_duty

        if update_data.max_concurrent_assignments is not None:
            staff.max_concurrent_assignments = update_data.max_concurrent_assignments

        if update_data.contact_preferences is not None:
            staff.contact_preferences = update_data.contact_preferences.model_dump()

        staff.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(staff)

        logger.info(f"Staff updated: id={staff_id}")

        return staff

    def update_duty_status(self, staff_id: UUID, on_duty: bool) -> Optional[StaffProfile]:
        """Update a staff member's on-duty status"""
        staff = self.get_staff(staff_id)
        if not staff:
            return None

        staff.on_duty = on_duty
        staff.updated_at = datetime.utcnow()

        self.db.commit()
        self.db.refresh(staff)

        logger.info(f"Staff duty status updated: id={staff_id}, on_duty={on_duty}")

        return staff

    def delete_staff(self, staff_id: UUID) -> bool:
        """Delete a staff profile"""
        staff = self.get_staff(staff_id)
        if not staff:
            return False

        self.db.delete(staff)
        self.db.commit()

        logger.info(f"Staff deleted: id={staff_id}")

        return True

    # =========================================================================
    # LOCATION TRACKING
    # =========================================================================

    def update_location(
        self,
        staff_id: UUID,
        location_data: StaffLocationUpdate,
    ) -> Optional[StaffLocation]:
        """
        Update a staff member's location.

        Args:
            staff_id: The staff member
            location_data: The new location data

        Returns:
            The created location record or None if staff not found
        """
        staff = self.get_staff(staff_id)
        if not staff:
            return None

        location = StaffLocation(
            staff_id=staff_id,
            zone_id=location_data.zone_id,
            building=location_data.building,
            floor=location_data.floor,
            source=location_data.source,
        )

        self.db.add(location)
        self.db.commit()
        self.db.refresh(location)

        logger.debug(f"Staff location updated: staff={staff_id}, zone={location_data.zone_id}")

        return location

    def get_current_location(self, staff_id: UUID) -> Optional[StaffLocation]:
        """Get a staff member's most recent location"""
        return (
            self.db.query(StaffLocation)
            .filter(StaffLocation.staff_id == staff_id)
            .order_by(desc(StaffLocation.timestamp))
            .first()
        )

    def get_location_history(
        self,
        staff_id: UUID,
        limit: int = 20,
    ) -> List[StaffLocation]:
        """Get a staff member's recent location history"""
        return (
            self.db.query(StaffLocation)
            .filter(StaffLocation.staff_id == staff_id)
            .order_by(desc(StaffLocation.timestamp))
            .limit(limit)
            .all()
        )

    # =========================================================================
    # STAFF AVAILABILITY & WORKLOAD
    # =========================================================================

    def get_active_assignment_count(self, staff_id: UUID) -> int:
        """Get count of active (non-resolved) alerts assigned to a staff member"""
        return (
            self.db.query(Alert)
            .filter(
                Alert.assigned_to == staff_id,
                Alert.status != AlertStatus.RESOLVED,
            )
            .count()
        )

    def is_available_for_assignment(self, staff_id: UUID) -> bool:
        """
        Check if a staff member is available for new assignments.

        Returns True if:
        - Staff is on duty
        - Staff has not reached max concurrent assignments
        """
        staff = self.get_staff(staff_id)
        if not staff:
            return False

        if not staff.on_duty:
            return False

        current_count = self.get_active_assignment_count(staff_id)
        return current_count < staff.max_concurrent_assignments

    def get_available_staff(
        self,
        role: Optional[StaffRoleEnum] = None,
        exclude_ids: Optional[List[UUID]] = None,
    ) -> List[StaffProfile]:
        """
        Get all staff members available for assignment.

        Args:
            role: Filter by role
            exclude_ids: Staff IDs to exclude

        Returns:
            List of available staff
        """
        query = self.db.query(StaffProfile).filter(StaffProfile.on_duty == True)

        if role:
            query = query.filter(StaffProfile.role == StaffRole(role.value))

        if exclude_ids:
            query = query.filter(~StaffProfile.id.in_(exclude_ids))

        staff_list = query.all()

        # Filter by availability (concurrent assignments)
        available = []
        for staff in staff_list:
            if self.is_available_for_assignment(staff.id):
                available.append(staff)

        return available

    # =========================================================================
    # PROXIMITY-BASED QUERIES
    # =========================================================================

    def get_staff_in_zone(self, zone_id: str) -> List[StaffProfile]:
        """Get all staff currently in a specific zone"""
        # Subquery to get latest location per staff
        latest_locations = (
            self.db.query(
                StaffLocation.staff_id,
                func.max(StaffLocation.timestamp).label("max_timestamp")
            )
            .group_by(StaffLocation.staff_id)
            .subquery()
        )

        # Join with locations to get staff in zone
        staff_ids = (
            self.db.query(StaffLocation.staff_id)
            .join(
                latest_locations,
                and_(
                    StaffLocation.staff_id == latest_locations.c.staff_id,
                    StaffLocation.timestamp == latest_locations.c.max_timestamp,
                )
            )
            .filter(StaffLocation.zone_id == zone_id)
            .all()
        )

        if not staff_ids:
            return []

        return (
            self.db.query(StaffProfile)
            .filter(StaffProfile.id.in_([s[0] for s in staff_ids]))
            .all()
        )

    def get_nearby_staff(
        self,
        zone_id: str,
        adjacent_zones: List[str],
        exclude_ids: Optional[List[UUID]] = None,
        on_duty_only: bool = True,
    ) -> List[Tuple[StaffProfile, str, int]]:
        """
        Get staff near a zone, sorted by proximity.

        Args:
            zone_id: The target zone
            adjacent_zones: List of adjacent zone IDs (ordered by distance)
            exclude_ids: Staff IDs to exclude
            on_duty_only: Only include on-duty staff

        Returns:
            List of tuples: (staff, current_zone, distance_rank)
            where distance_rank is 0 for same zone, 1 for first adjacent, etc.
        """
        # Build zone list with distance ranks
        zone_distances = {zone_id: 0}
        for i, adj_zone in enumerate(adjacent_zones):
            zone_distances[adj_zone] = i + 1

        all_zones = [zone_id] + adjacent_zones

        # Get latest locations for all staff
        latest_locations = (
            self.db.query(
                StaffLocation.staff_id,
                func.max(StaffLocation.timestamp).label("max_timestamp")
            )
            .group_by(StaffLocation.staff_id)
            .subquery()
        )

        # Get staff with their current zones
        results = (
            self.db.query(StaffProfile, StaffLocation.zone_id)
            .join(StaffLocation, StaffProfile.id == StaffLocation.staff_id)
            .join(
                latest_locations,
                and_(
                    StaffLocation.staff_id == latest_locations.c.staff_id,
                    StaffLocation.timestamp == latest_locations.c.max_timestamp,
                )
            )
            .filter(StaffLocation.zone_id.in_(all_zones))
        )

        if on_duty_only:
            results = results.filter(StaffProfile.on_duty == True)

        if exclude_ids:
            results = results.filter(~StaffProfile.id.in_(exclude_ids))

        results = results.all()

        # Add distance rank and sort
        nearby = []
        for staff, current_zone in results:
            distance = zone_distances.get(current_zone, 999)
            nearby.append((staff, current_zone, distance))

        # Sort by distance, then by name
        nearby.sort(key=lambda x: (x[2], x[0].name))

        return nearby

    def get_staff_with_location(self, staff_id: UUID) -> Optional[Tuple[StaffProfile, Optional[StaffLocation]]]:
        """Get a staff profile with their current location"""
        staff = self.get_staff(staff_id)
        if not staff:
            return None

        location = self.get_current_location(staff_id)
        return (staff, location)

    # =========================================================================
    # STATISTICS
    # =========================================================================

    def get_staff_statistics(self, staff_id: UUID) -> dict:
        """
        Get statistics for a staff member.

        Returns:
            Dictionary with stats like total alerts, avg response time, etc.
        """
        staff = self.get_staff(staff_id)
        if not staff:
            return {}

        # Count alerts by status
        active_count = self.get_active_assignment_count(staff_id)

        resolved_count = (
            self.db.query(Alert)
            .filter(
                Alert.resolved_by == staff_id,
                Alert.status == AlertStatus.RESOLVED,
            )
            .count()
        )

        total_assigned = (
            self.db.query(Alert)
            .filter(Alert.assigned_to == staff_id)
            .count()
        )

        return {
            "staff_id": str(staff_id),
            "name": staff.name,
            "role": staff.role.value,
            "on_duty": staff.on_duty,
            "active_alerts": active_count,
            "resolved_alerts": resolved_count,
            "total_assigned": total_assigned,
            "max_concurrent": staff.max_concurrent_assignments,
            "available_capacity": staff.max_concurrent_assignments - active_count,
        }
