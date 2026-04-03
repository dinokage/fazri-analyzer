"""
Hikvision ISAPI Access Control Simulator.

Simulates the Hikvision AcsEvent search endpoint so the HikvisionISAPIClient
can be tested without real hardware.

Start:
    uvicorn backend.simulators.hikvision_simulator:app --port 9011
    # or with continuous event generation:
    uvicorn backend.simulators.hikvision_simulator:app --port 9011 & python -m backend.simulators.hikvision_simulator --continuous
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import random
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json

logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request, Response, HTTPException, status
from fastapi.responses import PlainTextResponse

# Load zone and profile data
try:
    from scripts.sample_zones import ZONES_DATA
    ZONE_IDS = [z["zone_id"] for z in ZONES_DATA]
except Exception:
    ZONE_IDS = ["LIB_ENT", "LAB_101", "CAF_01", "HOSTEL_GATE", "GYM"]

# Load sample entity IDs from CSV for realistic data
SAMPLE_ENTITIES: list = []
_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "augmented", "student_staff_profiles.csv",
)
if os.path.exists(_CSV_PATH):
    import csv
    with open(_CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if i >= 200:
                break
            card_id = row.get("card_id", "")
            entity_id = row.get("entity_id", "")
            name = row.get("name", "Unknown")
            if card_id:
                SAMPLE_ENTITIES.append({"card_id": card_id, "entity_id": entity_id, "name": name})

if not SAMPLE_ENTITIES:
    SAMPLE_ENTITIES = [
        {"card_id": "C1234", "entity_id": "E100001", "name": "Test User"},
        {"card_id": "C5678", "entity_id": "E100002", "name": "Test Staff"},
    ]

# In-memory event store for the simulator
_events: list = []
_serial_counter = 1000

# Module-level async Redis client (initialised on startup)
_redis = None
_background_tasks: list = []


async def _get_redis():
    """Return an async Redis client, or None if unavailable."""
    try:
        import redis.asyncio as aioredis
        client = aioredis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            db=0,
            socket_timeout=2,
            socket_connect_timeout=2,
        )
        await client.ping()
        return client
    except Exception as exc:
        logger.warning("Hikvision sim: Redis unavailable (%s) — falling back to random events", exc)
        return None


def _make_event(entity: dict, zone_id: str, granted: bool = True) -> dict:
    global _serial_counter
    _serial_counter += 1
    return {
        "serial_no": str(_serial_counter),
        "datetime": datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
        "employee_no": entity["entity_id"],
        "card_no": entity["card_id"],
        "name": entity["name"],
        "door_no": str(ZONE_IDS.index(zone_id) + 1 if zone_id in ZONE_IDS else 1),
        "event_type": "1",
        "major": "5",
        "minor": "1" if granted else "38",
        "verify_mode": "cardOrFace",
    }


def _events_to_xml(events: list, total_matched: int, max_results: int = 20) -> str:
    """Render a list of event dicts as Hikvision ISAPI AcsEventSearchResult XML."""
    root = ET.Element("AcsEventSearchResult")
    root.set("xmlns", "http://www.hikvision.com/ver20/XMLSchema")

    status_el = ET.SubElement(root, "responseStatusStrg")
    status_el.text = "NO MORE" if len(events) < max_results else "MORE"

    num_el = ET.SubElement(root, "numOfMatches")
    num_el.text = str(len(events))

    matched_el = ET.SubElement(root, "totalMatches")
    matched_el.text = str(total_matched)

    info_el = ET.SubElement(root, "AcsEventInfo")

    for ev in events:
        ev_el = ET.SubElement(info_el, "AcsEvent")

        def sub(tag: str, text: str) -> None:
            el = ET.SubElement(ev_el, tag)
            el.text = text

        sub("dateTime", ev["datetime"])
        sub("employeeNoString", ev["employee_no"])
        sub("cardNo", ev["card_no"])
        sub("name", ev["name"])
        sub("doorNo", ev["door_no"])
        sub("eventType", ev["event_type"])
        sub("major", ev["major"])
        sub("minor", ev["minor"])
        sub("serialNo", ev["serial_no"])
        sub("currentVerifyMode", ev["verify_mode"])

    return '<?xml version="1.0" encoding="UTF-8" ?>\n' + ET.tostring(
        root, encoding="unicode"
    )


def _device_info_xml() -> str:
    return """<?xml version="1.0" encoding="UTF-8" ?>
<DeviceInfo xmlns="http://www.hikvision.com/ver20/XMLSchema">
  <deviceName>Hikvision Simulator</deviceName>
  <deviceID>FAZRI-SIM-001</deviceID>
  <model>DS-K1T671TM-3XF</model>
  <serialNumber>SIM20260402001</serialNumber>
  <macAddress>00:11:22:33:44:55</macAddress>
  <firmwareVersion>V2.2.4</firmwareVersion>
  <firmwareReleasedDate>20260101</firmwareReleasedDate>
</DeviceInfo>
"""


# ---------------------------------------------------------------------------
# Digest auth helpers (simplified — for simulation only)
# ---------------------------------------------------------------------------

_REALM = "FAZRI-Simulator"
_AUTH_USERNAME = os.getenv("HIKVISION_SIM_USER", "admin")
_AUTH_PASSWORD = os.getenv("HIKVISION_SIM_PASS", "admin123")


def _require_digest(request: Request) -> None:
    """Validate Digest auth header.  Returns 401 with WWW-Authenticate if missing."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Digest "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            headers={
                "WWW-Authenticate": (
                    f'Digest realm="{_REALM}", '
                    'qop="auth", '
                    'nonce="simulated_nonce_value", '
                    'opaque="simulated_opaque"'
                )
            },
        )
    # For simulation, just check username is present — skip full HA1/HA2 math
    if f'username="{_AUTH_USERNAME}"' not in auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Hikvision ISAPI Simulator")


@app.post("/ISAPI/AccessControl/AcsEvent/search")
async def search_acs_events(request: Request) -> Response:
    """Simulate POST /ISAPI/AccessControl/AcsEvent/search."""
    _require_digest(request)

    body = await request.body()
    search_position = 0
    max_results = 20
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

    try:
        tree = ET.fromstring(body)
        ns = {"h": "http://www.hikvision.com/ver20/XMLSchema"}
        # Fix: client sends <searchResultPosition>, not <searchPosition>
        pos_el = tree.find(".//searchResultPosition")
        if pos_el is None:
            pos_el = tree.find(".//h:searchResultPosition", ns)
        max_el = tree.find(".//maxResults")
        if max_el is None:
            max_el = tree.find(".//h:maxResults", ns)
        start_el = tree.find(".//startTime")
        if start_el is None:
            start_el = tree.find(".//h:startTime", ns)
        end_el = tree.find(".//endTime")
        if end_el is None:
            end_el = tree.find(".//h:endTime", ns)
        if pos_el is not None:
            search_position = int(pos_el.text or 0)
        if max_el is not None:
            max_results = int(max_el.text or 20)
        if start_el is not None and start_el.text:
            try:
                start_time = datetime.fromisoformat(start_el.text.replace("Z", "+00:00"))
            except ValueError:
                pass
        if end_el is not None and end_el.text:
            try:
                end_time = datetime.fromisoformat(end_el.text.replace("Z", "+00:00"))
            except ValueError:
                pass
    except Exception as exc:
        logger.debug("Failed to parse XML body: %s | excerpt: %s", exc, body[:200])

    # Apply time filter so re-polls don't return already-ingested events
    filtered = _events
    if start_time or end_time:
        filtered = []
        for ev in _events:
            try:
                ev_dt = datetime.fromisoformat(ev["datetime"].replace("Z", "+00:00"))
                if start_time and ev_dt < start_time:
                    continue
                if end_time and ev_dt > end_time:
                    continue
                filtered.append(ev)
            except (ValueError, KeyError):
                filtered.append(ev)

    page = filtered[search_position: search_position + max_results]
    xml_body = _events_to_xml(page, len(filtered), max_results)
    return Response(content=xml_body, media_type="application/xml")


@app.post("/ISAPI/System/deviceInfo")
@app.get("/ISAPI/System/deviceInfo")
async def get_device_info(request: Request) -> Response:
    """Return simulated device info."""
    _require_digest(request)
    return Response(content=_device_info_xml(), media_type="application/xml")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "events_in_store": len(_events)}


# ---------------------------------------------------------------------------
# Seed initial events on startup
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def seed_events() -> None:
    """Pre-populate the event store with a batch of historical events."""
    now = datetime.now(timezone.utc)
    for i in range(30):
        entity = random.choice(SAMPLE_ENTITIES)
        zone = random.choice(ZONE_IDS)
        ev = _make_event(entity, zone, granted=random.random() > 0.1)
        # Spread events over last 30 minutes
        ev["datetime"] = (now - timedelta(minutes=30 - i)).astimezone().strftime(
            "%Y-%m-%dT%H:%M:%S%z"
        )
        _events.append(ev)


# ---------------------------------------------------------------------------
# --continuous mode: original random event generator (fallback)
# ---------------------------------------------------------------------------

async def _continuous_generator() -> None:
    """Background task that generates random access events (Redis-unavailable fallback)."""
    while True:
        entity = random.choice(SAMPLE_ENTITIES)
        zone = random.choice(ZONE_IDS)
        _events.append(_make_event(entity, zone, granted=random.random() > 0.1))
        if len(_events) > 10_000:
            del _events[:5_000]
        await asyncio.sleep(random.uniform(2, 5))


# ---------------------------------------------------------------------------
# Coordinator-driven event generator (primary mode when Redis is available)
# ---------------------------------------------------------------------------

async def _coordinator_driven_generator() -> None:
    """
    Reads entity positions from Redis (written by MovementCoordinator) and
    appends RFID events to _events whenever an entity arrives at a new zone.

    Fires RFID ACCESS_GRANTED at `since_rfid` time using the entity's real
    card_id from entity_identifiers — making events resolvable by the backend.
    """
    global _redis
    last_zone: dict = {}  # entity_id → last zone an RFID event was fired for
    consecutive_failures = 0

    while True:
        now = datetime.now(timezone.utc)
        try:
            if await _redis.exists("sim:hikvision:paused"):
                await asyncio.sleep(3)
                continue
            raw_eids = await _redis.smembers("sim:active_entities")
            for raw_eid in raw_eids:
                eid = raw_eid.decode() if isinstance(raw_eid, bytes) else raw_eid
                raw = await _redis.get(f"sim:entity:{eid}")
                if not raw:
                    continue
                info = json.loads(raw)
                if info.get("traveling"):
                    continue
                zone = info["zone_id"]
                since_rfid = datetime.fromisoformat(info["since_rfid"])
                if zone != last_zone.get(eid) and since_rfid <= now:
                    entity = {
                        "card_id":   info["card_id"],
                        "entity_id": eid,
                        "name":      info.get("name", ""),
                    }
                    _events.append(_make_event(entity, zone, granted=True))
                    last_zone[eid] = zone
                    if len(_events) > 10_000:
                        del _events[:5_000]
            consecutive_failures = 0
        except Exception as exc:
            consecutive_failures += 1
            logger.warning("Hikvision sim coordinator generator error: %s", exc)
            if consecutive_failures >= 5:
                logger.warning("Attempting Redis reconnect after %d consecutive failures", consecutive_failures)
                _redis = await _get_redis()
                consecutive_failures = 0

        await asyncio.sleep(3)


@app.on_event("startup")
async def maybe_start_continuous() -> None:
    global _redis
    _redis = await _get_redis()

    continuous = os.getenv("HIKVISION_SIM_CONTINUOUS", "").lower() in ("1", "true", "yes")
    coordinator = os.getenv("HIKVISION_SIM_COORDINATOR", "").lower() in ("1", "true", "yes")

    if coordinator and _redis is not None:
        from simulators.movement_coordinator import run_coordinator
        _background_tasks.append(asyncio.create_task(run_coordinator(_redis)))

    if continuous:
        if _redis is not None:
            _background_tasks.append(asyncio.create_task(_coordinator_driven_generator()))
        else:
            _background_tasks.append(asyncio.create_task(_continuous_generator()))

@app.on_event("shutdown")
async def shutdown_simulators() -> None:
    for task in _background_tasks:
        task.cancel()
    if _background_tasks:
        await asyncio.gather(*_background_tasks, return_exceptions=True)


if __name__ == "__main__":
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="Hikvision ISAPI Simulator")
    parser.add_argument("--continuous", action="store_true", help="Generate events continuously")
    parser.add_argument("--port", type=int, default=9011)
    args = parser.parse_args()

    if args.continuous:
        os.environ["HIKVISION_SIM_CONTINUOUS"] = "1"

    uvicorn.run(app, host="0.0.0.0", port=args.port)
