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
import os
import random
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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


def _events_to_xml(events: list, total_matched: int) -> str:
    """Render a list of event dicts as Hikvision ISAPI AcsEventSearchResult XML."""
    root = ET.Element("AcsEventSearchResult")
    root.set("xmlns", "http://www.hikvision.com/ver20/XMLSchema")

    status_el = ET.SubElement(root, "responseStatusStrg")
    status_el.text = "NO MORE" if len(events) < 50 else "MORE"

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

    try:
        tree = ET.fromstring(body)
        ns = {"h": "http://www.hikvision.com/ver20/XMLSchema"}
        pos_el = tree.find(".//searchPosition") or tree.find(".//h:searchPosition", ns)
        max_el = tree.find(".//maxResults") or tree.find(".//h:maxResults", ns)
        if pos_el is not None:
            search_position = int(pos_el.text or 0)
        if max_el is not None:
            max_results = int(max_el.text or 20)
    except Exception:
        pass

    page = _events[search_position: search_position + max_results]
    xml_body = _events_to_xml(page, len(_events))
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
# --continuous mode: emit a new event every 2-5 seconds
# ---------------------------------------------------------------------------

async def _continuous_generator() -> None:
    """Background task that generates random access events."""
    while True:
        entity = random.choice(SAMPLE_ENTITIES)
        zone = random.choice(ZONE_IDS)
        _events.append(_make_event(entity, zone, granted=random.random() > 0.1))
        # Keep the store bounded at 10 000 events
        if len(_events) > 10_000:
            del _events[:5_000]
        await asyncio.sleep(random.uniform(2, 5))


@app.on_event("startup")
async def maybe_start_continuous() -> None:
    if os.getenv("HIKVISION_SIM_CONTINUOUS", "").lower() in ("1", "true", "yes"):
        asyncio.create_task(_continuous_generator())


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
