"""
System health endpoint.

GET /api/v1/system/health — aggregate health of all FAZRI subsystems.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text

from auth.dependencies import require_staff
from auth.models import AuthenticatedUser
from config import settings
from database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/system", tags=["system"])

# Module start time for uptime calculation
_START_TIME = time.monotonic()

_pgvector_engine = None


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class ServiceHealth(BaseModel):
    status: str          # "up" | "down" | "degraded" | "polling" | "disabled"
    latency_ms: Optional[float] = None
    details: Optional[str] = None
    last_poll: Optional[str] = None
    error: Optional[str] = None
    paused: Optional[bool] = None  # set only for simulator-backed services


class SystemHealthResponse(BaseModel):
    status: str           # "healthy" | "degraded" | "unhealthy"
    services: dict[str, ServiceHealth]
    uptime_seconds: int
    version: str
    timestamp: str


# ---------------------------------------------------------------------------
# Individual service probes (each has its own timeout)
# ---------------------------------------------------------------------------


async def _probe_postgres(db: Session) -> ServiceHealth:
    t0 = time.monotonic()
    try:
        row = db.execute(text("SELECT COUNT(*) FROM sensor_events")).scalar()
        ms = round((time.monotonic() - t0) * 1000, 1)
        return ServiceHealth(status="up", latency_ms=ms, details=f"sensor_events: {row:,} rows")
    except Exception as exc:
        return ServiceHealth(status="down", error=str(exc))


async def _probe_pgvector() -> ServiceHealth:
    global _pgvector_engine
    t0 = time.monotonic()
    try:
        if _pgvector_engine is None:
            from sqlalchemy import create_engine
            _pgvector_engine = create_engine(
                settings.DEEPFACE_POSTGRES_URI, connect_args={"connect_timeout": 3}
            )
        with _pgvector_engine.connect() as conn:
            try:
                row = conn.execute(text("SELECT COUNT(*) FROM face_embeddings")).scalar()
                label = f"face_embeddings: {row} enrolled"
            except Exception:
                conn.execute(text("SELECT 1"))
                label = "connected"
        ms = round((time.monotonic() - t0) * 1000, 1)
        return ServiceHealth(status="up", latency_ms=ms, details=label)
    except Exception as exc:
        return ServiceHealth(status="down", error=str(exc))


async def _probe_neo4j() -> ServiceHealth:
    t0 = time.monotonic()
    driver = None
    try:
        from neo4j import AsyncGraphDatabase
        driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
        async with driver.session() as session:
            result = await session.run("MATCH (n) RETURN count(n) AS cnt")
            record = await result.single()
            cnt = record["cnt"] if record else 0
        ms = round((time.monotonic() - t0) * 1000, 1)
        return ServiceHealth(status="up", latency_ms=ms, details=f"{cnt:,} nodes")
    except Exception as exc:
        return ServiceHealth(status="down", error=str(exc))
    finally:
        if driver:
            await driver.close()


async def _probe_redis() -> ServiceHealth:
    t0 = time.monotonic()
    import redis.asyncio as aioredis
    r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, socket_timeout=2)
    try:
        await r.ping()
        info = await r.info("memory")
        used = info.get("used_memory_human", "?")
        max_mem = info.get("maxmemory_human", "unlimited")
        ms = round((time.monotonic() - t0) * 1000, 1)
        return ServiceHealth(status="up", latency_ms=ms, details=f"memory: {used} / {max_mem}")
    except Exception as exc:
        return ServiceHealth(status="down", error=str(exc))
    finally:
        await r.aclose()


async def _probe_deepface() -> ServiceHealth:
    if not settings.DEEPFACE_ENABLED:
        return ServiceHealth(status="disabled", details="DEEPFACE_ENABLED=false")
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.DEEPFACE_SERVER_URL}/health")
        ms = round((time.monotonic() - t0) * 1000, 1)
        if r.status_code == 200:
            body = r.json()
            model = body.get("model", "unknown")
            embeddings = body.get("embeddings", "?")
            return ServiceHealth(
                status="up",
                latency_ms=ms,
                details=f"model: {model}, {embeddings} embeddings",
            )
        return ServiceHealth(status="degraded", latency_ms=ms, details=f"HTTP {r.status_code}")
    except Exception as exc:
        return ServiceHealth(status="down", error=str(exc))


async def _probe_hikvision() -> ServiceHealth:
    if not settings.HIKVISION_ENABLED:
        return ServiceHealth(status="disabled", details="HIKVISION_ENABLED=false")
    import redis.asyncio as aioredis
    r = None
    try:
        r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, socket_timeout=1)
        last_poll_ts = await r.get("hikvision:last_poll")
        events_today = await r.get("hikvision:events_today")
        paused = bool(await r.exists("sim:hikvision:paused"))

        if last_poll_ts:
            last_poll_dt = datetime.fromisoformat(last_poll_ts.decode())
            age_s = (datetime.now(timezone.utc) - last_poll_dt).total_seconds()
            age_str = f"{int(age_s)}s ago" if age_s < 120 else f"{int(age_s/60)}m ago"
        else:
            age_str = "never"

        events = int(events_today) if events_today else 0
        return ServiceHealth(
            status="polling",
            last_poll=age_str,
            details=f"events today: {events:,}",
            paused=paused,
        )
    except Exception as exc:
        return ServiceHealth(status="degraded", error=str(exc))
    finally:
        if r:
            await r.aclose()


async def _probe_aruba() -> ServiceHealth:
    if not settings.ARUBA_ENABLED:
        return ServiceHealth(status="disabled", details="ARUBA_ENABLED=false")
    import redis.asyncio as aioredis
    r = None
    try:
        r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, socket_timeout=1)
        last_poll_ts = await r.get("aruba:last_poll")
        clients_online = await r.get("aruba:clients_online")
        paused = bool(await r.exists("sim:aruba:paused"))

        if last_poll_ts:
            last_poll_dt = datetime.fromisoformat(last_poll_ts.decode())
            age_s = (datetime.now(timezone.utc) - last_poll_dt).total_seconds()
            age_str = f"{int(age_s)}s ago" if age_s < 120 else f"{int(age_s/60)}m ago"
        else:
            age_str = "never"

        clients = int(clients_online) if clients_online else 0
        return ServiceHealth(
            status="polling",
            last_poll=age_str,
            details=f"clients online: {clients}",
            paused=paused,
        )
    except Exception as exc:
        return ServiceHealth(status="degraded", error=str(exc))
    finally:
        if r:
            await r.aclose()


async def _probe_go2rtc() -> ServiceHealth:
    if not settings.GO2RTC_ENABLED:
        return ServiceHealth(status="disabled", details="GO2RTC_ENABLED=false")
    t0 = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{settings.GO2RTC_API_URL}/api/streams")
        ms = round((time.monotonic() - t0) * 1000, 1)
        if r.status_code == 200:
            streams = r.json()
            count = len(streams) if isinstance(streams, dict) else 0
            return ServiceHealth(status="up", latency_ms=ms, details=f"active streams: {count}")
        return ServiceHealth(status="degraded", latency_ms=ms, details=f"HTTP {r.status_code}")
    except Exception as exc:
        return ServiceHealth(status="down", error=str(exc))


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/health",
    response_model=SystemHealthResponse,
    summary="System health",
    description="Returns aggregate health of all FAZRI subsystems.",
)
async def system_health(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> SystemHealthResponse:
    # Run all probes concurrently; individual exceptions are caught inside each probe
    results = await asyncio.gather(
        _probe_postgres(db),
        _probe_pgvector(),
        _probe_neo4j(),
        _probe_redis(),
        _probe_deepface(),
        _probe_hikvision(),
        _probe_aruba(),
        _probe_go2rtc(),
        return_exceptions=False,
    )

    services: dict[str, ServiceHealth] = {
        "postgres":       results[0],
        "pgvector":       results[1],
        "neo4j":          results[2],
        "redis":          results[3],
        "deepface_server": results[4],
        "hikvision":      results[5],
        "aruba":          results[6],
        "go2rtc":         results[7],
    }

    # Determine overall status
    # Critical services: postgres, redis — if down/degraded → unhealthy/degraded
    # Non-critical: any down or degraded → degraded
    critical = {"postgres", "redis"}
    has_critical_down = any(services[s].status == "down" for s in critical)
    has_critical_degraded = any(services[s].status == "degraded" for s in critical)
    has_any_down = any(v.status == "down" for v in services.values())
    has_any_degraded = any(v.status == "degraded" for v in services.values())

    if has_critical_down:
        overall = "unhealthy"
    elif has_critical_degraded or has_any_down or has_any_degraded:
        overall = "degraded"
    else:
        overall = "healthy"

    return SystemHealthResponse(
        status=overall,
        services=services,
        uptime_seconds=int(time.monotonic() - _START_TIME),
        version="0.2.0",
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# Simulator control endpoints
# ---------------------------------------------------------------------------

_SIM_PAUSE_KEYS: dict[str, str] = {
    "hikvision": "sim:hikvision:paused",
    "aruba":     "sim:aruba:paused",
}


@router.post(
    "/simulators/{sim}/pause",
    summary="Pause a simulator",
    description="Sets the Redis pause flag so the named simulator stops generating events.",
)
async def pause_simulator(
    sim: str,
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> dict:
    if sim not in _SIM_PAUSE_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown simulator '{sim}'. Valid: {list(_SIM_PAUSE_KEYS)}")
    import redis.asyncio as aioredis
    r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, socket_timeout=2)
    try:
        await r.set(_SIM_PAUSE_KEYS[sim], "1", ex=86400)
        return {"sim": sim, "paused": True}
    finally:
        await r.aclose()


@router.post(
    "/simulators/{sim}/resume",
    summary="Resume a simulator",
    description="Removes the Redis pause flag so the named simulator resumes generating events.",
)
async def resume_simulator(
    sim: str,
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> dict:
    if sim not in _SIM_PAUSE_KEYS:
        raise HTTPException(status_code=404, detail=f"Unknown simulator '{sim}'. Valid: {list(_SIM_PAUSE_KEYS)}")
    import redis.asyncio as aioredis
    r = aioredis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0, socket_timeout=2)
    try:
        await r.delete(_SIM_PAUSE_KEYS[sim])
        return {"sim": sim, "paused": False}
    finally:
        await r.aclose()
