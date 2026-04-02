"""
Aruba AOS8 REST API Simulator.

Simulates the Aruba AOS8 controller's monitoring endpoints for WiFi client
associations and AP status.

Start:
    uvicorn backend.simulators.aruba_simulator:app --port 9002
"""

from __future__ import annotations

import asyncio
import csv
import json
import logging
import os
import random
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Query, HTTPException, status, Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Sample data setup
# ---------------------------------------------------------------------------

try:
    from scripts.sample_zones import ZONES_DATA
    ZONE_IDS = [z["zone_id"] for z in ZONES_DATA]
except Exception:
    ZONE_IDS = ["LIB_ENT", "LAB_101", "CAF_01", "HOSTEL_GATE", "GYM"]

# Map zone_id → AP name (one AP per zone for simplicity)
ZONE_TO_AP: Dict[str, str] = {
    zone: f"AP-{zone.replace('_', '-')}-01" for zone in ZONE_IDS
}
AP_TO_ZONE: Dict[str, str] = {v: k for k, v in ZONE_TO_AP.items()}

# Load device_hash values from CSV
SAMPLE_DEVICES: List[Dict] = []
_CSV_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "augmented", "student_staff_profiles.csv",
)
if os.path.exists(_CSV_PATH):
    with open(_CSV_PATH, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        for i, row in enumerate(reader):
            if i >= 150:
                break
            dh = row.get("device_hash", "")
            name = row.get("name", "Unknown")
            role = row.get("role", "student")
            if dh:
                # Convert device_hash to MAC-like format (6 pairs)
                mac = ":".join(
                    dh.lstrip("DH")[:12].ljust(12, "0")[i:i+2]
                    for i in range(0, 12, 2)
                )
                SAMPLE_DEVICES.append({
                    "mac": mac,
                    "device_hash": dh,
                    "name": f"{name.split()[0]}-phone",
                    "role": role,
                })

if not SAMPLE_DEVICES:
    SAMPLE_DEVICES = [
        {"mac": "aa:bb:cc:dd:ee:01", "device_hash": "DH001", "name": "test-phone", "role": "student"},
        {"mac": "aa:bb:cc:dd:ee:02", "device_hash": "DH002", "name": "staff-phone", "role": "staff"},
    ]

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

_sessions: Dict[str, datetime] = {}  # token → expiry

# Module-level async Redis client (set on startup)
_redis = None


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
        logger.warning("Aruba sim: Redis unavailable (%s) — falling back to random clients", exc)
        return None


def _random_clients() -> List[Dict]:
    """Return a randomised subset of device clients, each on a random AP."""
    n = random.randint(10, min(40, len(SAMPLE_DEVICES)))
    selected = random.sample(SAMPLE_DEVICES, n)
    now = datetime.now(timezone.utc)
    clients = []
    for dev in selected:
        ap = random.choice(list(ZONE_TO_AP.values()))
        zone = AP_TO_ZONE[ap]
        assoc_delta = timedelta(minutes=random.randint(1, 120))
        clients.append({
            "MAC": dev["mac"],
            "Name": dev["name"],
            "IP": f"10.1.{random.randint(1, 10)}.{random.randint(10, 250)}",
            "AP name": ap,
            "ESSID": "KIIT-Student" if dev["role"] == "student" else "KIIT-Staff",
            "Status": "Associated",
            "Role": dev["role"],
            "Phy": random.choice(["ax-5GHz-40MHz", "ac-5GHz-80MHz", "n-2.4GHz-20MHz"]),
            "Signal": str(random.randint(-75, -40)),
            "Speed (mbps)": str(random.choice([54, 144, 300, 450, 573, 1200])),
            "Association Time": (now - assoc_delta).isoformat(),
        })
    return clients


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------

app = FastAPI(title="Aruba AOS8 Simulator")

# Cached client list — used as fallback when Redis is unavailable
_cached_clients: List[Dict] = []


@app.on_event("startup")
async def init_clients() -> None:
    global _redis, _cached_clients
    _redis = await _get_redis()
    # Pre-populate fallback cache; also start legacy random mover if Redis unavailable
    _cached_clients = _random_clients()
    if _redis is None:
        asyncio.create_task(_movement_simulator())


async def _movement_simulator() -> None:
    """Legacy random movement — only runs when Redis (coordinator) is unavailable."""
    global _cached_clients
    while True:
        await asyncio.sleep(random.uniform(30, 60))
        clients = list(_cached_clients)
        n_move = max(1, len(clients) // 8)
        for _ in range(n_move):
            if not clients:
                break
            idx = random.randint(0, len(clients) - 1)
            clients[idx]["AP name"] = random.choice(list(ZONE_TO_AP.values()))
            clients[idx]["Association Time"] = datetime.now(timezone.utc).isoformat()
        _cached_clients = clients


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/v1/api/login")
async def login(response: Response, username: str = "", password: str = "") -> dict:
    """Issue a session token."""
    # Accept any credentials in simulator mode
    token = str(uuid.uuid4())
    _sessions[token] = datetime.now(timezone.utc) + timedelta(hours=8)
    response.set_cookie("UIDARUBA", token, max_age=28800)
    return {
        "GlobalResult": {
            "status": "0",
            "status_str": "success",
            "UIDARUBA": token,
        }
    }


@app.post("/v1/api/logout")
async def logout(UIDARUBA: str = Query(default="")) -> dict:
    _sessions.pop(UIDARUBA, None)
    return {"GlobalResult": {"status": "0", "status_str": "success"}}


def _validate_session(token: str) -> None:
    if token not in _sessions:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired or invalid",
        )
    if datetime.now(timezone.utc) > _sessions[token]:
        del _sessions[token]
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
        )


# ---------------------------------------------------------------------------
# Monitoring endpoints
# ---------------------------------------------------------------------------

@app.get("/v1/monitoring/client")
async def get_clients(UIDARUBA: str = Query(default="")) -> dict:
    """Return currently associated WiFi clients.

    When Redis is available, reads coordinator positions so that WiFi events
    always agree with RFID events (same entity, same zone).  Falls back to
    the cached random client list when Redis is unavailable.
    """
    _validate_session(UIDARUBA)

    if _redis is None:
        return {"Clients": _cached_clients}

    now = datetime.now(timezone.utc)
    clients: List[Dict] = []
    try:
        raw_eids = await _redis.smembers("sim:active_entities")
        for raw_eid in raw_eids:
            eid = raw_eid.decode() if isinstance(raw_eid, bytes) else raw_eid
            raw = await _redis.get(f"sim:entity:{eid}")
            if not raw:
                continue
            info = json.loads(raw)
            if info.get("traveling"):
                continue
            wifi_since = datetime.fromisoformat(info["since_wifi"])
            if wifi_since > now:
                continue  # entity's phone hasn't associated yet
            zone_id = info["zone_id"]
            ap_name = ZONE_TO_AP.get(zone_id, f"AP-{zone_id}-01")
            name    = info.get("name", "")
            clients.append({
                "MAC":              info["mac"],  # verbatim lowercase from entity_identifiers
                "Name":             f"{name.split()[0] if name else eid}-phone",
                "IP":               f"10.1.{random.randint(1, 254)}.{random.randint(1, 254)}",
                "AP name":          ap_name,
                "ESSID":            "KIIT-Student",
                "Status":           "Associated",
                "Role":             "student",
                "Phy":              random.choice(["ax-5GHz-40MHz", "ac-5GHz-80MHz"]),
                "Signal":           str(random.randint(-75, -40)),
                "Speed (mbps)":     "300",
                "Association Time": info["since_wifi"],
            })
    except Exception as exc:
        logger.warning("Aruba sim: Redis read failed (%s) — returning cached clients", exc)
        return {"Clients": _cached_clients}

    return {"Clients": clients}


@app.get("/v1/monitoring/ap")
async def get_aps(UIDARUBA: str = Query(default="")) -> dict:
    """Return list of access points."""
    _validate_session(UIDARUBA)
    aps = [
        {
            "Name": ap_name,
            "Zone": zone,
            "Status": "Up",
            "IP": f"10.10.{i}.1",
            "Clients": sum(1 for c in _cached_clients if c["AP name"] == ap_name),
        }
        for i, (zone, ap_name) in enumerate(ZONE_TO_AP.items())
    ]
    return {"APs": aps}


@app.get("/health")
async def health() -> dict:
    coordinator_active = _redis is not None
    return {
        "status": "ok",
        "coordinator_mode": coordinator_active,
        "active_sessions": len(_sessions),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)
