"""
Movement Coordinator — shared entity position state for simulator sync.

Writes per-entity zone positions to Redis so that the Hikvision simulator
(RFID events) and Aruba simulator (WiFi clients) always agree on where
each entity is at any given time.

Redis schema
------------
sim:coordinator:lock        — leader-election key; TTL=30s, refreshed every 20s
sim:active_entities         — Redis SET of active entity_ids; TTL=7200
sim:entity:{entity_id}      — JSON blob; TTL=7200
  {
    "zone_id":    "LIB_ENT",
    "since_rfid": "2026-04-03T10:01:00Z",   # RFID fires at/after this time
    "since_wifi": "2026-04-03T10:01:08Z",   # WiFi fires at/after this (5-15s later)
    "traveling":  false,                     # true while entity is in transit
    "card_id":    "C3286",
    "mac":        "dh6d0bd80c8f8e",          # lowercased from entity_identifiers
    "name":       "Neha Mehta"
  }
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import sys
from datetime import datetime, timezone, timedelta
from typing import Dict, List
from urllib.parse import unquote

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

LOCK_KEY   = "sim:coordinator:lock"
ACTIVE_KEY = "sim:active_entities"
ENTITY_KEY = "sim:entity:{}"

LOCK_TTL  = 30    # seconds; coordinator refreshes every 20s
DATA_TTL  = 7200  # 2-hour expiry on entity position keys

DWELL_MIN = 180   # minimum seconds per zone (3 min)
DWELL_MAX = 600   # maximum seconds per zone (10 min)

NUM_ENTITIES = int(os.getenv("SIM_NUM_ENTITIES", "10"))


# ---------------------------------------------------------------------------
# Zone data
# ---------------------------------------------------------------------------

try:
    from scripts.sample_zones import ZONES_DATA
    _ZONE_IDS: List[str] = [z["zone_id"] for z in ZONES_DATA]
except Exception:
    _ZONE_IDS = ["LIB_ENT", "LAB_101", "CAF_01", "HOSTEL_GATE", "GYM", "AUDITORIUM", "ADMIN_LOBBY"]


def _travel_seconds(from_zone: str, to_zone: str) -> int:
    """Return realistic travel time between two zones using zone_matrix."""
    try:
        from config.zone_matrix import zone_matrix
        return zone_matrix.get_min_travel_time(from_zone, to_zone)
    except Exception:
        return 120  # fallback: 2-minute walk


# ---------------------------------------------------------------------------
# Entity loading
# ---------------------------------------------------------------------------

def _load_entities_from_db() -> List[Dict]:
    """
    Query entity_identifiers via psycopg2 directly (no ORM) to get
    entities that have both a card_id and a mac_address registered.
    Returns list of {entity_id, card_id, mac (lowercase), name}.
    """
    try:
        import psycopg2  # type: ignore
    except ImportError:
        logger.warning("MovementCoordinator: psycopg2 not installed — skipping DB load")
        return []

    try:
        # POSTGRES_PASSWORD may be URL-encoded (e.g. %40 for @) when stored in
        # Jenkins credentials for use in SQLAlchemy URLs. psycopg2 takes the
        # raw password, so decode it first.
        conn = psycopg2.connect(
            host=os.getenv("POSTGRES_SERVER", "db"),
            port=int(os.getenv("POSTGRES_PORT", "5432")),
            user=os.getenv("POSTGRES_USER", "postgres"),
            password=unquote(os.getenv("POSTGRES_PASSWORD", "")),
            dbname=os.getenv("POSTGRES_DB", "ethos_iitg"),
            connect_timeout=5,
        )
        with conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT ei1.entity_id,
                           ei1.identifier_value        AS card_id,
                           LOWER(ei2.identifier_value) AS mac,
                           ep.name
                    FROM   entity_identifiers ei1
                    JOIN   entity_identifiers ei2
                           ON  ei1.entity_id       = ei2.entity_id
                           AND ei2.identifier_type  = 'mac_address'
                           AND ei2.active           = true
                    JOIN   entity_profiles ep
                           ON  ep.entity_id = ei1.entity_id
                    WHERE  ei1.identifier_type = 'card_id'
                      AND  ei1.active = true
                    LIMIT  100
                """)
                rows = cur.fetchall()
        conn.close()
        entities = [
            {"entity_id": r[0], "card_id": r[1], "mac": r[2], "name": r[3] or ""}
            for r in rows
        ]
        logger.info("MovementCoordinator: loaded %d entities from DB", len(entities))
        return entities
    except Exception as exc:
        logger.warning("MovementCoordinator: DB load failed (%s) — falling back to CSV", exc)
        return []


def _load_entities_from_csv() -> List[Dict]:
    """Fallback: load entities from the augmented CSV using the same MAC derivation as the Aruba sim."""
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    csv_path = os.path.join(here, "augmented", "student_staff_profiles.csv")
    entities: List[Dict] = []
    try:
        import csv as _csv
        with open(csv_path, newline="", encoding="utf-8") as fh:
            for i, row in enumerate(_csv.DictReader(fh)):
                if i >= 100:
                    break
                card_id   = row.get("card_id", "")
                dh        = row.get("device_hash", "")
                entity_id = row.get("entity_id", "")
                name      = row.get("name", "")
                if card_id and dh and entity_id:
                    mac = dh.lower()  # matches LOWER(identifier_value) from the DB path
                    entities.append({"entity_id": entity_id, "card_id": card_id, "mac": mac, "name": name})
    except Exception as exc:
        logger.warning("MovementCoordinator: CSV fallback failed: %s", exc)
    return entities


def load_entities() -> List[Dict]:
    entities = _load_entities_from_db()
    if not entities:
        entities = _load_entities_from_csv()
    if not entities:
        logger.error("MovementCoordinator: no entities found — movement simulation is disabled")
    return entities


# ---------------------------------------------------------------------------
# Per-entity movement task
# ---------------------------------------------------------------------------

async def _entity_task(entity: Dict, redis) -> None:
    """
    Drive one entity's random walk forever.

    Sequence per move:
      1. Write arrival position to Redis (RFID fires immediately, WiFi after 5-15s).
      2. Dwell for DWELL_MIN–DWELL_MAX seconds.
      3. Mark entity as 'traveling'.
      4. Sleep for the realistic travel time to next zone.
      5. Arrive at new zone — repeat.
    """
    eid          = entity["entity_id"]
    current_zone = random.choice(_ZONE_IDS)

    while True:
        now        = datetime.now(timezone.utc)
        wifi_delay = random.uniform(5, 15)

        position: Dict = {
            "zone_id":    current_zone,
            "since_rfid": now.isoformat(),
            "since_wifi": (now + timedelta(seconds=wifi_delay)).isoformat(),
            "traveling":  False,
            "card_id":    entity["card_id"],
            "mac":        entity["mac"],
            "name":       entity["name"],
        }

        try:
            await redis.set(ENTITY_KEY.format(eid), json.dumps(position), ex=DATA_TTL)
            await redis.sadd(ACTIVE_KEY, eid)
            await redis.expire(ACTIVE_KEY, DATA_TTL)
        except Exception as exc:
            logger.warning("MovementCoordinator: Redis write failed for %s: %s", eid, exc)

        # Stay in zone
        await asyncio.sleep(random.uniform(DWELL_MIN, DWELL_MAX))

        # Pick next zone
        candidates = [z for z in _ZONE_IDS if z != current_zone]
        next_zone  = random.choice(candidates) if candidates else current_zone
        travel_secs = _travel_seconds(current_zone, next_zone)

        # Mark as traveling so simulators suppress events during transit
        try:
            traveling_pos = dict(position)
            traveling_pos["traveling"] = True
            await redis.set(ENTITY_KEY.format(eid), json.dumps(traveling_pos), ex=DATA_TTL)
        except Exception:
            pass

        await asyncio.sleep(travel_secs)
        current_zone = next_zone


# ---------------------------------------------------------------------------
# Coordinator entry point
# ---------------------------------------------------------------------------

async def run_coordinator(redis) -> None:
    """
    Leader-elected coordinator — only one instance is active across all processes.

    Uses Redis SET NX EX as a distributed lock.  The winning instance refreshes
    the lock every 20s.  If it dies, the lock expires after 30s and another
    instance takes over automatically.
    """
    entities = load_entities()
    if not entities:
        return

    active_entities = random.sample(entities, min(NUM_ENTITIES, len(entities)))

    # Compete for coordinator lock
    while True:
        acquired = await redis.set(LOCK_KEY, "1", nx=True, ex=LOCK_TTL)
        if acquired:
            break
        logger.debug("MovementCoordinator: lock held by another instance — retrying in 5s")
        await asyncio.sleep(5)

    logger.info(
        "MovementCoordinator started — %d entities active (leader elected)",
        len(active_entities),
    )

    tasks = [
        asyncio.create_task(_entity_task(entity, redis))
        for entity in active_entities
    ]

    # Refresh the lock on a dead-man's timer
    try:
        while True:
            await asyncio.sleep(20)
            await redis.expire(LOCK_KEY, LOCK_TTL)
    except asyncio.CancelledError:
        for t in tasks:
            t.cancel()
        raise
