"""
End-to-end integration test for the FAZRI sensor pipeline.

Prerequisites (start with docker compose before running):
  docker compose -f docker-compose.test.yml up -d
  # Wait for backend to become healthy (~30s)
  pytest backend/tests/test_integration_e2e.py -v

The test:
  1. Seeds entity data via SAP CSV import
  2. Waits 15 s for the Hikvision + Aruba pollers to ingest events
  3. Asserts DB-level pipeline results
  4. Asserts the API returns the correct data shapes

Environment (matches docker-compose.test.yml):
  TEST_BACKEND_URL  — default http://localhost:18000
  TEST_JWT_SECRET   — default "fazri-integration-test-jwt-secret"
  TEST_DB_URL       — default postgresql://postgres:testpassword@localhost:15432/ethos_test
"""

from __future__ import annotations

import asyncio
import os
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

import httpx
import pytest
import pytest_asyncio
from jose import jwt
from sqlalchemy import create_engine, text

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BACKEND_URL = os.getenv("TEST_BACKEND_URL", "http://localhost:18000")
JWT_SECRET = os.getenv("TEST_JWT_SECRET", "fazri-integration-test-jwt-secret")
DB_URL = os.getenv(
    "TEST_DB_URL",
    "postgresql://postgres:testpassword@localhost:15432/ethos_test",
)

_AUGMENTED_CSV = Path(__file__).parent.parent / "augmented" / "student_staff_profiles.csv"
_FIXTURE_CSV   = Path(__file__).parent / "fixtures" / "test_profiles.csv"
CSV_PATH = _AUGMENTED_CSV if _AUGMENTED_CSV.exists() else _FIXTURE_CSV

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_token(role: str = "SUPER_ADMIN", entity_id: str = "test-admin-001") -> str:
    """Mint an HS256 token accepted by the backend when TESTING=true."""
    payload = {
        "id": "test-user-id",
        "entity_id": entity_id,
        "name": "Integration Tester",
        "email": "test@fazri.campus",
        "role": role,
        "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def auth_headers(role: str = "SUPER_ADMIN") -> dict[str, str]:
    return {"Authorization": f"Bearer {make_token(role=role)}"}


def db_engine():
    return create_engine(DB_URL, connect_args={"connect_timeout": 10})


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    eng = db_engine()
    yield eng
    eng.dispose()


@pytest_asyncio.fixture(scope="module")
async def client():
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=30) as c:
        yield c


# ---------------------------------------------------------------------------
# Step 1: Wait for backend to be ready
# ---------------------------------------------------------------------------


@pytest.mark.order(1)
@pytest.mark.asyncio
async def test_backend_health(client: httpx.AsyncClient):
    """Backend must be reachable before any other test runs."""
    deadline = time.time() + 60
    last_exc: Exception | None = None
    while time.time() < deadline:
        try:
            r = await client.get("/health")
            if r.status_code == 200:
                assert r.json()["status"] == "healthy"
                return
        except httpx.TransportError as exc:
            last_exc = exc
        await asyncio.sleep(2)
    raise AssertionError(f"Backend not healthy after 60s: {last_exc}")


# ---------------------------------------------------------------------------
# Step 2: Seed entity data
# ---------------------------------------------------------------------------


@pytest.mark.order(2)
@pytest.mark.asyncio
async def test_seed_entity_data(client: httpx.AsyncClient):
    """POST the augmented CSV to /api/v1/import/sap-csv and assert entities seeded."""
    assert CSV_PATH.exists(), f"CSV not found: {CSV_PATH}"

    with open(CSV_PATH, "rb") as fh:
        r = await client.post(
            "/api/v1/import/sap-csv",
            files={"file": ("student_staff_profiles.csv", fh, "text/csv")},
            headers=auth_headers(),
        )

    assert r.status_code == 200, f"Import failed: {r.text}"
    body = r.json()
    assert body.get("created", 0) + body.get("updated", 0) > 0, (
        f"No entities seeded: {body}"
    )


# ---------------------------------------------------------------------------
# Step 3: Wait for pollers to ingest events
# ---------------------------------------------------------------------------


@pytest.mark.order(3)
@pytest.mark.asyncio
async def test_wait_for_poller_events(engine):
    """
    Poll the sensor_events table every 2 s for up to 60 s, waiting until
    at least one RFID event and one WIFI event have been ingested.
    """
    deadline = time.time() + 60
    with engine.connect() as conn:
        while time.time() < deadline:
            row = conn.execute(
                text(
                    "SELECT "
                    "COUNT(*) FILTER (WHERE sensor_type = 'RFID') AS rfid_count, "
                    "COUNT(*) FILTER (WHERE sensor_type = 'WIFI') AS wifi_count "
                    "FROM sensor_events"
                )
            ).fetchone()
            if row and row.rfid_count > 0 and row.wifi_count > 0:
                return
            await asyncio.sleep(2)
    pytest.fail("Pollers did not produce RFID and WIFI events within 60 s")


# ---------------------------------------------------------------------------
# Step 4: DB-level assertions
# ---------------------------------------------------------------------------


@pytest.mark.order(4)
def test_rfid_events_in_db(engine):
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM sensor_events WHERE sensor_type = 'RFID'")
        ).scalar()
    assert count > 0, "No RFID events found in sensor_events"


@pytest.mark.order(5)
def test_wifi_events_in_db(engine):
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM sensor_events WHERE sensor_type = 'WIFI'")
        ).scalar()
    assert count > 0, "No WIFI events found in sensor_events"


@pytest.mark.order(6)
def test_some_events_resolved(engine):
    """At least one event should have been entity-resolved (resolved_entity_id != NULL)."""
    with engine.connect() as conn:
        count = conn.execute(
            text(
                "SELECT COUNT(*) FROM sensor_events "
                "WHERE resolved_entity_id IS NOT NULL"
            )
        ).scalar()
    assert count > 0, (
        "No resolved events found — entity resolution service may not be working"
    )


@pytest.mark.order(7)
def test_entity_profiles_seeded(engine):
    with engine.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM entity_profiles")
        ).scalar()
    assert count > 0, "entity_profiles table is empty — seeding step may have failed"


# ---------------------------------------------------------------------------
# Step 5: First resolved entity (for API tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def known_entity_id(engine) -> str:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                "SELECT resolved_entity_id FROM sensor_events "
                "WHERE resolved_entity_id IS NOT NULL LIMIT 1"
            )
        ).fetchone()
    assert row is not None, "No resolved entity found for API tests"
    return row[0]


# ---------------------------------------------------------------------------
# Step 6: API-level assertions
# ---------------------------------------------------------------------------


@pytest.mark.order(8)
@pytest.mark.asyncio
async def test_events_api_returns_mixed_types(client: httpx.AsyncClient):
    """GET /api/v1/events must return events from multiple sensor types."""
    r = await client.get(
        "/api/v1/events",
        params={"limit": 200},
        headers=auth_headers(),
    )
    assert r.status_code == 200, f"Events API error: {r.text}"
    body = r.json()
    assert body["total"] > 0, "Events API returned 0 events"
    types_seen = {ev["sensor_type"] for ev in body["items"]}
    assert len(types_seen) >= 2, (
        f"Expected events from ≥2 sensor types, got: {types_seen}"
    )


@pytest.mark.order(9)
@pytest.mark.asyncio
async def test_entity_timeline_api(
    client: httpx.AsyncClient, known_entity_id: str
):
    """GET /api/v1/entities/{entity_id}/timeline must return events for the entity."""
    r = await client.get(
        f"/api/v1/entities/{known_entity_id}/timeline",
        params={"limit": 50},
        headers=auth_headers(),
    )
    assert r.status_code == 200, (
        f"Timeline API error for entity {known_entity_id}: {r.text}"
    )
    body = r.json()
    assert body["entity_id"] == known_entity_id
    assert body["total"] > 0, (
        f"Timeline returned 0 events for entity {known_entity_id}"
    )
    # Verify chronological order (ASC)
    timestamps = [ev["timestamp"] for ev in body["events"]]
    assert timestamps == sorted(timestamps), "Timeline events are not sorted ASC"


@pytest.mark.order(10)
@pytest.mark.asyncio
async def test_events_filter_by_sensor_type(client: httpx.AsyncClient):
    """Filtering by sensor_type=RFID must return only RFID events."""
    r = await client.get(
        "/api/v1/events",
        params={"sensor_type": "RFID", "limit": 50},
        headers=auth_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    if body["total"] > 0:
        types = {ev["sensor_type"] for ev in body["items"]}
        assert types == {"RFID"}, f"Non-RFID events returned: {types}"


@pytest.mark.order(11)
@pytest.mark.asyncio
async def test_events_filter_resolved_only(client: httpx.AsyncClient):
    """resolved=true filter must return only events with a resolved entity."""
    r = await client.get(
        "/api/v1/events",
        params={"resolved": "true", "limit": 50},
        headers=auth_headers(),
    )
    assert r.status_code == 200
    body = r.json()
    for ev in body["items"]:
        assert ev["resolved_entity_id"] is not None, (
            f"resolved=true filter returned unresolved event: {ev['event_id']}"
        )
