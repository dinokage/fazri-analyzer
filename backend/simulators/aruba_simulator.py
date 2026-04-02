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
import os
import random
import sys
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Query, HTTPException, status, Response
from fastapi.responses import JSONResponse

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

# Current client associations: mac → {ap, zone, assoc_time}
_current_clients: Dict[str, Dict] = {}
_last_movement: datetime = datetime.now(timezone.utc)


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

# Cached client list, refreshed periodically to simulate movement
_cached_clients: List[Dict] = []


@app.on_event("startup")
async def init_clients() -> None:
    global _cached_clients
    _cached_clients = _random_clients()
    asyncio.create_task(_movement_simulator())


async def _movement_simulator() -> None:
    """Simulate clients moving between APs every 30-60 seconds."""
    global _cached_clients
    while True:
        await asyncio.sleep(random.uniform(30, 60))
        # Move 10-20% of clients to different APs
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
    """Return currently associated WiFi clients."""
    _validate_session(UIDARUBA)
    return {"Clients": _cached_clients}


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
    return {
        "status": "ok",
        "clients_online": len(_cached_clients),
        "active_sessions": len(_sessions),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9002)
