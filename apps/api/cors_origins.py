import asyncio
import logging
import re

import redis.asyncio as aioredis

from config import settings

logger = logging.getLogger(__name__)

REDIS_KEY = "fazri:trusted_origins"
REFRESH_INTERVAL_SECONDS = 300  # 5 minutes — matches auth service cadence

_dynamic_origins: set[str] = set()

# Compiled static patterns — allow all subdomains of the base domain and any
# configured extra domains, plus localhost for dev.
_STATIC_PATTERNS: list[re.Pattern[str]] = []

def _build_static_patterns() -> list[re.Pattern[str]]:
    base = re.escape(settings.FAZRI_BASE_DOMAIN)
    patterns = [
        re.compile(rf"^https?://([a-zA-Z0-9-]+\.)*{base}$"),
        re.compile(r"^http://localhost(:[0-9]+)?$"),
    ]
    for extra in settings.EXTRA_CORS_ORIGINS:
        try:
            patterns.append(re.compile(re.escape(extra)))
        except re.error:
            logger.warning(f"[cors-origins] Invalid extra origin pattern: {extra!r}")
    return patterns


def _get_redis() -> aioredis.Redis:
    return aioredis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        decode_responses=True,
        socket_connect_timeout=2,
    )


async def _load_from_redis() -> set[str]:
    r = _get_redis()
    try:
        members = await r.smembers(REDIS_KEY)
        return set(members)
    except Exception as exc:
        logger.warning(f"[cors-origins] Redis load failed: {exc}")
        return set()
    finally:
        await r.aclose()


async def init_cors_origins() -> None:
    global _dynamic_origins, _STATIC_PATTERNS
    _STATIC_PATTERNS = _build_static_patterns()
    origins = await _load_from_redis()
    _dynamic_origins = origins
    logger.info(
        f"[cors-origins] Initialized — {len(origins)} custom domain(s) from Redis,"
        f" {len(_STATIC_PATTERNS)} static pattern(s)"
    )


async def _refresh_loop() -> None:
    global _dynamic_origins
    while True:
        await asyncio.sleep(REFRESH_INTERVAL_SECONDS)
        try:
            origins = await _load_from_redis()
            _dynamic_origins = origins
            logger.debug(f"[cors-origins] Refreshed — {len(origins)} custom domain(s)")
        except Exception as exc:
            logger.warning(f"[cors-origins] Refresh failed: {exc}")


def start_refresh_task() -> asyncio.Task:
    return asyncio.create_task(_refresh_loop())


def is_allowed_origin(origin: str | None) -> bool:
    if not origin:
        return True
    for pattern in _STATIC_PATTERNS:
        if pattern.fullmatch(origin):
            return True
    return origin in _dynamic_origins
