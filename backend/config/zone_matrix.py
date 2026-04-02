"""
Zone travel time matrix for campus anomaly detection.

Provides realistic minimum travel times (seconds) between any pair of campus
zones.  Used by DeepFaceAnomalyAnalyzer.impossible_travel to decide whether
a cross-zone detection is physically possible.

Usage
-----
    from config.zone_matrix import zone_matrix

    t = zone_matrix.get_min_travel_time("LIB_ENT", "HOSTEL_GATE")  # seconds
    impossible = zone_matrix.is_impossible_travel("LIB_ENT", "LAB_101", 15)  # True

CLI
---
    python -m backend.config.zone_matrix   # prints the full matrix as a table
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Zone source data — imported once at module load
# ---------------------------------------------------------------------------
from scripts.sample_zones import ZONES_DATA

# Walking parameters
_WALKING_SPEED_MS = 1.4          # metres per second (≈ 5 km/h)
_PATH_TORTUOSITY = 1.4           # straight-line × factor = real path length
_SAME_FLOOR_SECONDS = 30         # minimum for zones in same building & floor
_PER_FLOOR_SECONDS = 60          # extra seconds per floor traversed
_MIN_CROSS_BUILDING_SECONDS = 60 # floor-crossing minimum for inter-building
_DEFAULT_UNKNOWN_SECONDS = 120   # returned when either zone is not in matrix


# ---------------------------------------------------------------------------
# Internal zone config
# ---------------------------------------------------------------------------


@dataclass
class ZoneConfig:
    """Lightweight zone descriptor for the matrix calculator."""

    zone_id: str
    name: str
    building: str
    floor: int
    lat: float
    lng: float


# ---------------------------------------------------------------------------
# Matrix calculation helpers
# ---------------------------------------------------------------------------


def _haversine_metres(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Straight-line distance in metres between two (lat, lng) coordinates.
    Uses the Haversine formula — accurate for distances < 1 km.
    """
    R = 6_371_000  # Earth radius in metres
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)

    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_travel_matrix(
    zones: List[ZoneConfig],
) -> Dict[Tuple[str, str], int]:
    """
    Compute minimum travel seconds for every ordered (zone_a, zone_b) pair.

    Rules (in order of application):
    1. Same zone → 0 seconds.
    2. Same building, same floor → 30 seconds.
    3. Same building, different floor → 60 s × abs(floor difference).
    4. Different buildings → Haversine × 1.4 / 1.4 m/s, minimum 60 seconds.

    The matrix is symmetric: time(A→B) == time(B→A).
    """
    matrix: Dict[Tuple[str, str], int] = {}

    for i, za in enumerate(zones):
        for j, zb in enumerate(zones):
            if za.zone_id == zb.zone_id:
                matrix[(za.zone_id, zb.zone_id)] = 0
                continue

            # Always compute the canonical (lower, upper) entry once
            if i > j:
                # Mirror the already-computed pair
                matrix[(za.zone_id, zb.zone_id)] = matrix[
                    (zb.zone_id, za.zone_id)
                ]
                continue

            same_building = za.building.strip().lower() == zb.building.strip().lower()

            if same_building:
                floor_diff = abs(za.floor - zb.floor)
                if floor_diff == 0:
                    seconds = _SAME_FLOOR_SECONDS
                else:
                    seconds = floor_diff * _PER_FLOOR_SECONDS
            else:
                straight_m = _haversine_metres(za.lat, za.lng, zb.lat, zb.lng)
                path_m = straight_m * _PATH_TORTUOSITY
                seconds = max(
                    _MIN_CROSS_BUILDING_SECONDS,
                    int(path_m / _WALKING_SPEED_MS),
                )

            # Store both directions
            matrix[(za.zone_id, zb.zone_id)] = seconds
            matrix[(zb.zone_id, za.zone_id)] = seconds

    return matrix


# ---------------------------------------------------------------------------
# ZoneMatrixConfig
# ---------------------------------------------------------------------------


class ZoneMatrixConfig:
    """
    Module-level singleton holding all zone configs and the travel time matrix.

    Attributes
    ----------
    zones : dict[str, ZoneConfig]
        All campus zones, keyed by zone_id.
    matrix : dict[tuple[str, str], int]
        Minimum travel seconds for each (zone_a, zone_b) pair.
    """

    def __init__(self) -> None:
        self.zones: Dict[str, ZoneConfig] = self._load_zones()
        self.matrix: Dict[Tuple[str, str], int] = calculate_travel_matrix(
            list(self.zones.values())
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_min_travel_time(self, zone_a: str, zone_b: str) -> int:
        """
        Return minimum travel seconds between zone_a and zone_b.

        Returns:
            0 when zone_a == zone_b.
            The computed matrix value when both zones are known.
            120 (``_DEFAULT_UNKNOWN_SECONDS``) when either zone is unknown.
        """
        if zone_a == zone_b:
            return 0
        return self.matrix.get(
            (zone_a, zone_b),
            _DEFAULT_UNKNOWN_SECONDS,
        )

    def is_impossible_travel(
        self,
        zone_a: str,
        zone_b: str,
        elapsed_seconds: int,
    ) -> bool:
        """
        Return True when ``elapsed_seconds`` is less than the minimum travel
        time between zone_a and zone_b — meaning a real person could not have
        physically moved between the two zones in that time.
        """
        min_time = self.get_min_travel_time(zone_a, zone_b)
        return elapsed_seconds < min_time

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _load_zones() -> Dict[str, ZoneConfig]:
        zones: Dict[str, ZoneConfig] = {}
        for z in ZONES_DATA:
            coords = z.get("coordinates", {})
            zones[z["zone_id"]] = ZoneConfig(
                zone_id=z["zone_id"],
                name=z["name"],
                building=z.get("building", "Unknown"),
                floor=int(z.get("floor", 1)),
                lat=float(coords.get("lat", 0.0)),
                lng=float(coords.get("lng", 0.0)),
            )
        return zones


# ---------------------------------------------------------------------------
# Module-level singleton — auto-calculates on first import
# ---------------------------------------------------------------------------

zone_matrix = ZoneMatrixConfig()


# ---------------------------------------------------------------------------
# CLI: python -m backend.config.zone_matrix
# ---------------------------------------------------------------------------

def _print_matrix() -> None:
    """Print the travel time matrix as a readable table."""
    zm = zone_matrix
    zone_ids = sorted(zm.zones.keys())

    col_w = 14

    # Header row
    header = "From \\ To".ljust(col_w) + "".join(z.ljust(col_w) for z in zone_ids)
    print(header)
    print("-" * len(header))

    for za in zone_ids:
        row = za.ljust(col_w)
        for zb in zone_ids:
            t = zm.get_min_travel_time(za, zb)
            row += (f"{t}s").ljust(col_w)
        print(row)

    print()
    print("Legend: seconds of minimum walking time between zone pairs")


if __name__ == "__main__":
    _print_matrix()
