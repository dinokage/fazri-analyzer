"""
DeepFace Anomaly Analyzer.

Pure analysis logic: no database calls, no HTTP calls.
Accepts dicts in, returns an anomaly dict or None.

This keeps the anomaly rules independently testable without any fixtures.

Anomaly types produced:
    low_confidence_match       — face matched but distance is suspiciously high
    unauthorized_zone_access   — entity detected in a zone they are not cleared for
    impossible_travel          — same entity detected in two zones too close in time
    unknown_entity             — face detected but not found in the campus DB
                                 (only raised when alert_on_unknown_face=True)

Usage:
    from services.deepface_anomaly import DeepFaceAnomalyAnalyzer

    result = DeepFaceAnomalyAnalyzer.analyze(
        match={"img_name": "ENT-001", "distance": 0.38, "confidence": 62.0, "threshold": 0.40},
        entity={"entity_id": "ENT-001", "name": "Alice", "role": "STUDENT"},
        zone_id="LAB_301",
        authorized_zones=["LIB_ENT", "CAF_01"],
        recent_detections=[...],
        alert_on_unknown_face=True,
    )
    # result is either None or {"anomaly_type": ..., "severity": ..., "description": ..., "details": ...}
"""

from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from config import settings


class DeepFaceAnomalyAnalyzer:
    """
    Stateless anomaly rule engine for DeepFace face-match events.

    All methods are class methods (no instance state) so callers never need
    to instantiate the class.
    """

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    @classmethod
    def analyze(
        cls,
        match: Optional[Dict[str, Any]],
        entity: Optional[Dict[str, Any]],
        zone_id: str,
        authorized_zones: List[str],
        recent_detections: List[Dict[str, Any]],
        alert_on_unknown_face: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Run all anomaly rules against a single face-match event.

        Args:
            match: The FaceMatch dict from the webhook payload.  Pass None
                   when no match was found (unknown entity path).
            entity: Entity properties dict from Neo4j, or None if the
                    img_name could not be resolved to any entity.
            zone_id: The zone this camera covers.
            authorized_zones: List of zone_ids the entity may enter.
                              An empty list means "no zone restrictions set"
                              and is treated as fully authorized.
            recent_detections: DETECTED_IN events for this entity in the
                               last N minutes (from CctvGraphService).
            alert_on_unknown_face: Camera-level flag; when False an unknown
                                   face is logged but not alerted.

        Returns:
            A single anomaly dict for the highest-priority rule that fired,
            or None when everything looks normal.
        """

        # Rule 1 — Unknown entity (no entity found for img_name)
        if entity is None:
            return cls._unknown_entity(match, zone_id, alert_on_unknown_face)

        # Rule 2 — Impossible travel (check before zone auth so we catch it
        #           even if the entity *is* authorized in the new zone)
        impossible = cls._impossible_travel(entity, zone_id, recent_detections)
        if impossible:
            return impossible

        # Rule 3 — Unauthorized zone access
        unauthorized = cls._unauthorized_zone(entity, zone_id, authorized_zones)
        if unauthorized:
            return unauthorized

        # Rule 4 — Low confidence match (suspicious but within threshold)
        if match:
            low_conf = cls._low_confidence(match, entity, zone_id)
            if low_conf:
                return low_conf

        return None

    # ------------------------------------------------------------------
    # Rule implementations
    # ------------------------------------------------------------------

    @classmethod
    def _unknown_entity(
        cls,
        match: Optional[Dict[str, Any]],
        zone_id: str,
        alert_on_unknown_face: bool,
    ) -> Optional[Dict[str, Any]]:
        """
        Fires when a face was detected (match provided) but no entity in
        the campus database carries the matched img_name label — or when
        img_name is an unregistered label.

        Returns None when alert_on_unknown_face is False (log only).
        """
        if not alert_on_unknown_face:
            return None

        label = match.get("img_name", "unknown") if match else "unknown"
        distance = match.get("distance") if match else None
        confidence = match.get("confidence") if match else None

        detail_msg = (
            f"distance={distance:.3f} confidence={confidence:.1f}%"
            if distance is not None
            else "no match found in database"
        )

        return {
            "anomaly_type": "unknown_entity",
            "severity": "critical",
            "description": (
                f"Unidentified face detected in zone {zone_id}. "
                f"Label '{label}' not found in campus entity registry. "
                f"{detail_msg}"
            ),
            "details": {
                "img_name": label,
                "zone_id": zone_id,
                "distance": distance,
                "confidence": confidence,
                "rule": "unknown_entity",
            },
        }

    @classmethod
    def _impossible_travel(
        cls,
        entity: Dict[str, Any],
        current_zone_id: str,
        recent_detections: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """
        Fires when the entity was detected in a *different* zone more
        recently than DEEPFACE_IMPOSSIBLE_TRAVEL_MINUTES ago.

        Skips detections in the same zone (normal re-detection).
        """
        window = timedelta(minutes=settings.DEEPFACE_IMPOSSIBLE_TRAVEL_MINUTES)
        now = datetime.now(timezone.utc)
        cutoff = now - window

        for det in recent_detections:
            prev_zone = det.get("zone_id")
            if prev_zone == current_zone_id:
                continue  # Same zone — normal

            # Parse Neo4j datetime (may be a neo4j.time.DateTime or python datetime)
            raw_ts = det.get("timestamp")
            if raw_ts is None:
                continue

            # Coerce to aware python datetime
            if isinstance(raw_ts, datetime):
                prev_ts = raw_ts if raw_ts.tzinfo else raw_ts.replace(tzinfo=timezone.utc)
            else:
                try:
                    # neo4j.time.DateTime → ISO string → python datetime
                    prev_ts = datetime.fromisoformat(str(raw_ts)).replace(tzinfo=timezone.utc)
                except (ValueError, TypeError):
                    continue

            if prev_ts >= cutoff:
                entity_id = entity.get("entity_id", "unknown")
                entity_name = entity.get("name", entity_id)
                minutes_ago = int((now - prev_ts).total_seconds() / 60)
                return {
                    "anomaly_type": "impossible_travel",
                    "severity": "critical",
                    "description": (
                        f"Impossible travel detected for {entity_name} ({entity_id}). "
                        f"Seen in zone {prev_zone} {minutes_ago} minute(s) ago, "
                        f"now detected in zone {current_zone_id}."
                    ),
                    "details": {
                        "entity_id": entity_id,
                        "entity_name": entity_name,
                        "previous_zone": prev_zone,
                        "current_zone": current_zone_id,
                        "previous_detection_timestamp": prev_ts.isoformat(),
                        "minutes_between": minutes_ago,
                        "rule": "impossible_travel",
                    },
                }

        return None

    @classmethod
    def _unauthorized_zone(
        cls,
        entity: Dict[str, Any],
        zone_id: str,
        authorized_zones: List[str],
    ) -> Optional[Dict[str, Any]]:
        """
        Fires when the entity is detected in a zone they are not authorised
        to access.

        If authorized_zones is empty we assume no zone-restriction data is
        available and skip this rule to avoid false positives.
        """
        if not authorized_zones:
            # No access-permission graph data — skip rather than false-positive
            return None

        if zone_id in authorized_zones:
            return None

        entity_id = entity.get("entity_id", "unknown")
        entity_name = entity.get("name", entity_id)
        role = entity.get("role", "unknown")

        return {
            "anomaly_type": "unauthorized_zone_access",
            "severity": "high",
            "description": (
                f"{entity_name} ({entity_id}, role={role}) detected in zone "
                f"{zone_id} which they are not authorised to access. "
                f"Authorised zones: {', '.join(authorized_zones) or 'none'}."
            ),
            "details": {
                "entity_id": entity_id,
                "entity_name": entity_name,
                "entity_role": role,
                "detected_zone": zone_id,
                "authorized_zones": authorized_zones,
                "rule": "unauthorized_zone_access",
            },
        }

    @classmethod
    def _low_confidence(
        cls,
        match: Dict[str, Any],
        entity: Dict[str, Any],
        zone_id: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Fires when a face matched within the threshold but at a suspiciously
        high distance (distance >= LOW_CONFIDENCE_DISTANCE).

        This can indicate an impersonation attempt or poor image quality.
        """
        distance = match.get("distance", 0.0)
        threshold = match.get("threshold", settings.DEEPFACE_CONFIDENCE_THRESHOLD)
        confidence = match.get("confidence", 100.0)
        low_conf_floor = settings.DEEPFACE_LOW_CONFIDENCE_DISTANCE

        if distance < low_conf_floor:
            return None  # Normal, high-confidence match

        entity_id = entity.get("entity_id", "unknown")
        entity_name = entity.get("name", entity_id)

        return {
            "anomaly_type": "low_confidence_match",
            "severity": "medium",
            "description": (
                f"Low-confidence face match for {entity_name} ({entity_id}) "
                f"in zone {zone_id}. "
                f"Distance={distance:.3f} (threshold={threshold:.2f}, "
                f"confidence={confidence:.1f}%). "
                "Possible impersonation or poor image quality."
            ),
            "details": {
                "entity_id": entity_id,
                "entity_name": entity_name,
                "zone_id": zone_id,
                "distance": distance,
                "threshold": threshold,
                "confidence": confidence,
                "low_confidence_floor": low_conf_floor,
                "rule": "low_confidence_match",
            },
        }
