"""
DeepFace Integration Routes.

Endpoints:
  POST   /api/v1/deepface/webhook                              — Receive face-match events from DeepFace server (no auth)
  POST   /api/v1/deepface/streams                              — Register and start a camera stream (admin)
  GET    /api/v1/deepface/streams                              — List all camera streams (staff)
  PATCH  /api/v1/deepface/streams/{stream_id}                  — Update stream config (admin)
  DELETE /api/v1/deepface/streams/{stream_id}                  — Stop and remove a stream (admin)
  POST   /api/v1/deepface/entities/{entity_id}/register        — Register face photo (admin)
  GET    /api/v1/deepface/entities/{entity_id}/registration    — Check face registration status (staff)
  POST   /api/v1/deepface/search                               — Ad-hoc face search (staff)
  POST   /api/v1/deepface/index/build                          — Rebuild ANN index (admin)
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import io
import logging
import time
import psycopg2
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

import cv2
import httpx
from urllib.parse import quote
import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile, File, status
from fastapi.responses import StreamingResponse
from starlette.responses import Response
from sqlalchemy.orm import Session

from auth.dependencies import require_staff, require_admin
from auth.models import AuthenticatedUser
from config import settings
from database.connection import get_db
from models.db.camera_streams import CameraStream, CameraStreamStatus
from models.db.alerts import AlertSeverity, ActorType
from models.schemas.alerts import AlertCreate, AlertSeverityEnum, LocationSchema
from models.schemas.deepface import (
    FaceRegistrationResponse,
    FaceSearchResponse,
    FaceSearchResult,
    StreamCreateRequest,
    StreamListResponse,
    StreamResponse,
    StreamUpdateRequest,
    WebhookPayload,
    WebhookProcessedResponse,
)
from services.deepface_client import get_deepface_client
from services.cctv_graph_service import get_cctv_graph_service
from services.deepface_anomaly import DeepFaceAnomalyAnalyzer
from services.alerts.alert_service import AlertService
from services.alerts.assignment_engine import AssignmentEngine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/deepface", tags=["deepface"])


# ============================================================================
# Helpers
# ============================================================================


def _verify_webhook_signature(raw_body: bytes, signature_header: Optional[str]) -> None:
    """
    Validate the HMAC-SHA256 signature on the incoming webhook.

    The DeepFace server must set X-DeepFace-Signature to
    "sha256=<hex_digest>" computed over the raw request body.

    Raises HTTP 403 when verification fails.
    Skips verification entirely when DEEPFACE_WEBHOOK_SECRET is empty
    (development convenience — never leave empty in production).
    """
    secret = settings.DEEPFACE_WEBHOOK_SECRET
    if not secret:
        return  # Dev mode — skip

    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Missing X-DeepFace-Signature header",
        )

    # Expected format: "sha256=<hex>"
    parts = signature_header.split("=", 1)
    if len(parts) != 2 or parts[0] != "sha256":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid signature format (expected sha256=<hex>)",
        )

    expected = hmac.new(
        secret.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, parts[1]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Webhook signature mismatch",
        )


# ── Alert cooldown (Redis) ─────────────────────────────────────────────────
# Prevents duplicate alerts when the same face appears in consecutive frames.
# Uses Redis SET NX EX for atomic "create if absent" with auto-expiry.

_alert_redis: Any = None


def _get_alert_redis():
    global _alert_redis
    if _alert_redis is None:
        try:
            import redis as _redis_lib
            _alert_redis = _redis_lib.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            _alert_redis.ping()
            logger.debug("Alert cooldown Redis connected: %s:%s db=%s", settings.REDIS_HOST, settings.REDIS_PORT, settings.REDIS_DB)
        except Exception as exc:
            logger.warning("Alert cooldown Redis unavailable: %s — duplicates may occur", exc)
            _alert_redis = None
    return _alert_redis


def _cooldown_key(anomaly_type: str, stream_id: str, entity_key: str) -> str:
    return f"fazri:alert_cd:{anomaly_type}:{stream_id}:{entity_key}"


def _is_alert_suppressed(anomaly_type: str, stream_id: str, entity_key: str) -> bool:
    r = _get_alert_redis()
    if not r:
        logger.warning("Cooldown check skipped — Redis unavailable")
        return False
    key = _cooldown_key(anomaly_type, stream_id, entity_key)
    try:
        exists = r.exists(key) == 1
        logger.debug("Cooldown check: key=%s exists=%s", key, exists)
        return exists
    except Exception as exc:
        logger.error("Cooldown check failed for key=%s: %s", key, exc)
        return False


def _set_alert_cooldown(anomaly_type: str, stream_id: str, entity_key: str) -> None:
    r = _get_alert_redis()
    if not r:
        logger.warning("Cooldown set skipped — Redis unavailable")
        return
    key = _cooldown_key(anomaly_type, stream_id, entity_key)
    try:
        result = r.set(key, "1", ex=settings.ALERT_COOLDOWN_SECONDS, nx=True)
        logger.debug("Cooldown set: key=%s ttl=%s result=%s", key, settings.ALERT_COOLDOWN_SECONDS, result)
    except Exception as exc:
        logger.error("Cooldown set FAILED for key=%s: %s", key, exc)


def _go2rtc_register_url(stream_id: str, rtsp_url: str) -> str:
    """Build go2rtc stream registration URL.

    go2rtc API: PUT /api/streams?name={stream_name}&src={rtsp_url}
    Confirmed from go2rtc source (www/add.html):
      url.searchParams.set('name', streamName)
      url.searchParams.set('src', sourceUrl)
    """
    return (
        f"{settings.GO2RTC_API_URL}/api/streams"
        f"?name={quote(stream_id, safe='')}"
        f"&src={quote(rtsp_url, safe='')}"
    )


# ============================================================================


def _create_alert_from_anomaly(
    anomaly: Dict[str, Any],
    entity: Optional[Dict[str, Any]],
    zone_id: str,
    match_data: Optional[Dict[str, Any]],
    payload: WebhookPayload,
    db: Session,
) -> None:
    """
    Translate an anomaly dict into an Alert record and auto-assign it.

    Mirrors the two-step pattern from alert_routes.py lines 118-143:
      1. AlertService.create_alert()
      2. AssignmentEngine.assign_alert() or assign_critical_alert()
    """
    severity_map = {
        "low": AlertSeverityEnum.LOW,
        "medium": AlertSeverityEnum.MEDIUM,
        "high": AlertSeverityEnum.HIGH,
        "critical": AlertSeverityEnum.CRITICAL,
    }
    severity = severity_map.get(anomaly.get("severity", "medium"), AlertSeverityEnum.MEDIUM)

    affected = [entity["entity_id"]] if entity else []

    evidence: Dict[str, Any] = {
        "face_recognition": {
            "stream_id": payload.stream_id,
            "timestamp": payload.timestamp.isoformat(),
            "frames_processed": payload.frames_processed,
            "rtsp_url": payload.rtsp_url,
        },
        "cctv_frames": {
            "stream_id": payload.stream_id,
            "faces_found": payload.faces_found,
        },
        "anomaly_details": anomaly.get("details", {}),
    }

    if match_data:
        evidence["face_recognition"].update({
            "distance": match_data.get("distance"),
            "confidence": match_data.get("confidence"),
            "threshold": match_data.get("threshold"),
            "facial_area": match_data.get("facial_area"),
        })

    alert_data = AlertCreate(
        anomaly_type=anomaly["anomaly_type"],
        title=f"Face Recognition Alert: {anomaly['anomaly_type'].replace('_', ' ').title()}",
        description=anomaly["description"],
        severity=severity,
        location=LocationSchema(zone_id=zone_id),
        affected_entities=affected,
        data_sources=["CCTV"],
        evidence=evidence,
        is_mock=False,
    )

    alert_service = AlertService(db)
    alert = alert_service.create_alert(
        alert_data=alert_data,
        actor_type=ActorType.SYSTEM,
    )

    assignment_engine = AssignmentEngine(db)
    if alert.severity == AlertSeverity.CRITICAL:
        assigned = assignment_engine.assign_critical_alert(alert, max_assignees=3)
        if assigned:
            logger.info(
                "Critical deepface alert %s auto-assigned to %d staff",
                alert.id,
                len(assigned),
            )
    else:
        assigned = assignment_engine.assign_alert(alert)
        if assigned:
            logger.info(
                "Deepface alert %s auto-assigned to %s",
                alert.id,
                assigned.name,
            )

    db.refresh(alert)

    # Web Push to all subscribed browser sessions
    try:
        from services.push_service import send_push_to_all
        send_push_to_all(
            db=db,
            title=alert_data.title,
            body=alert_data.description[:120],
            url=f"/dashboard/alerts/{alert.id}",
        )
    except Exception as exc:
        logger.warning("Web Push delivery error: %s", exc)

    # Fire Discord webhook (non-blocking best-effort)
    if settings.DISCORD_WEBHOOK_URL:
        severity_colors = {
            "low": 3447003,       # blue
            "medium": 16776960,   # yellow
            "high": 16744272,     # orange
            "critical": 15158332, # red
        }
        color = severity_colors.get(anomaly.get("severity", "medium"), 15158332)
        discord_payload = {
            "content": "🚨 **Unknown Face Detected**",
            "embeds": [{
                "title": alert_data.title,
                "description": alert_data.description[:500],
                "color": color,
                "fields": [
                    {"name": "Severity", "value": anomaly.get("severity", "medium").upper(), "inline": True},
                    {"name": "Zone", "value": zone_id, "inline": True},
                    {"name": "Alert ID", "value": str(alert.id), "inline": False},
                ],
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }],
        }
        asyncio.create_task(_post_discord_webhook(settings.DISCORD_WEBHOOK_URL, discord_payload))


def _stream_to_response(stream: CameraStream) -> StreamResponse:
    return StreamResponse.model_validate(stream)


async def _post_discord_webhook(url: str, payload: Dict[str, Any]) -> None:
    """Fire-and-forget Discord webhook POST."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            await client.post(url, json=payload)
    except Exception as exc:
        logger.warning("Discord webhook delivery failed: %s", exc)


def _grab_rtsp_frame(rtsp_url: str, timeout_seconds: float = 5.0) -> bytes:
    """
    Blocking helper: open the RTSP stream, grab one frame, return it as JPEG bytes.
    Raises RuntimeError if a frame cannot be captured within the timeout.
    Intended to be run in a thread executor so it does not block the event loop.

    CAP_PROP_OPEN_TIMEOUT_MSEC limits the initial RTSP TCP/SDP handshake so a
    dead camera does not stall the thread indefinitely before cap.read() is called.
    CAP_PROP_READ_TIMEOUT_MSEC limits each individual read() call after connection.
    """
    timeout_ms = int(timeout_seconds * 1000)
    cap = cv2.VideoCapture()
    cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, timeout_ms)
    cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, timeout_ms)
    cap.open(rtsp_url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    deadline = time.monotonic() + timeout_seconds
    try:
        if not cap.isOpened():
            raise RuntimeError("Could not open RTSP stream — camera may be offline or URL incorrect")
        while time.monotonic() < deadline:
            ret, frame = cap.read()
            if ret and frame is not None:
                ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ok:
                    return buf.tobytes()
        raise RuntimeError("Could not grab a frame within the timeout")
    finally:
        cap.release()


# ============================================================================
# Webhook receiver
# ============================================================================


@router.post(
    "/webhook",
    response_model=WebhookProcessedResponse,
    summary="Receive face-match events from DeepFace server",
    description=(
        "Called automatically by the DeepFace server when a face is matched "
        "in an active RTSP stream. No authentication required — secured via "
        "HMAC-SHA256 signature (X-DeepFace-Signature header)."
    ),
)
async def deepface_webhook(
    request: Request,
    db: Session = Depends(get_db),
) -> WebhookProcessedResponse:
    """
    Core integration endpoint.

    For each face match in the payload:
      1. Validate HMAC signature
      2. Look up CameraStream config (zone_id, alert_on_unknown_face)
      3. Resolve entity from Neo4j by img_name (= entity_id)
      4. Write DETECTED_IN edge to Neo4j
      5. Run anomaly rules
      6. Create alert + auto-assign if anomaly detected
    """
    # Read raw body first (needed for signature verification)
    raw_body = await request.body()
    sig_header = request.headers.get("X-DeepFace-Signature")
    _verify_webhook_signature(raw_body, sig_header)

    # Parse payload (Pydantic does not consume the body stream so we pass raw)
    import json as _json
    try:
        payload_dict = _json.loads(raw_body)
        payload = WebhookPayload(**payload_dict)
    except Exception as exc:
        logger.warning("DeepFace webhook: failed to parse payload: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid webhook payload: {exc}",
        )

    # Look up camera stream config
    cam_stream: Optional[CameraStream] = (
        db.query(CameraStream)
        .filter(CameraStream.stream_id == payload.stream_id)
        .first()
    )

    if cam_stream is None:
        # Unknown stream — log and accept (don't 404, DeepFace would keep retrying)
        logger.warning(
            "Webhook received for unknown stream_id=%s — ignoring",
            payload.stream_id,
        )
        return WebhookProcessedResponse(status="ok", processed=0, alerts_created=0)

    zone_id = cam_stream.zone_id
    alert_on_unknown_face = cam_stream.alert_on_unknown_face

    graph_svc = get_cctv_graph_service()
    alerts_created = 0
    processed = 0
    detection_overlays: List[Dict[str, Any]] = []  # collected for Redis cache

    for match in payload.matches:
        entity_id = match.img_name
        match_dict = match.model_dump()

        # Resolve entity from Neo4j
        entity = graph_svc.get_entity_by_entity_id(entity_id)

        # Collect detection data for frontend bounding box overlays
        detection_overlays.append({
            "img_name": match.img_name,
            "entity_name": entity.get("name") if entity else None,
            "confidence": match.confidence,
            "distance": match.distance,
            "facial_area": match.facial_area.model_dump() if match.facial_area else None,
            "is_unknown": match.img_name == "UNKNOWN_FACE",
        })

        # Write detection event to Neo4j
        if entity is not None:
            graph_svc.create_detected_in(
                entity_id=entity_id,
                zone_id=zone_id,
                timestamp=payload.timestamp,
                stream_id=payload.stream_id,
                face_id=entity.get("face_id", entity_id),
            )
        else:
            # Log unknown face event
            graph_svc.create_unknown_detected_in(
                zone_id=zone_id,
                timestamp=payload.timestamp,
                stream_id=payload.stream_id,
            )

        # Gather data for anomaly analysis
        recent_detections: List[Dict[str, Any]] = []
        authorized_zones: List[str] = []

        if entity is not None:
            recent_detections = graph_svc.get_recent_detections(
                entity_id=entity_id,
                minutes=settings.DEEPFACE_IMPOSSIBLE_TRAVEL_MINUTES * 2,
            )
            authorized_zones = graph_svc.get_authorized_zones(entity_id)

        # Run anomaly rules
        anomaly = DeepFaceAnomalyAnalyzer.analyze(
            match=match_dict,
            entity=entity,
            zone_id=zone_id,
            authorized_zones=authorized_zones,
            recent_detections=recent_detections,
            alert_on_unknown_face=alert_on_unknown_face,
        )

        if anomaly and settings.ALERT_SYSTEM_ENABLED:
            anomaly_type = anomaly.get("anomaly_type", "unknown")
            # Known entity → entity_id for per-person cooldown.
            # Unknown face → stream-level key. Per-face tracker_ids are
            # unreliable because search() and represent() don't guarantee
            # the same face ordering, causing unstable IDs.
            entity_key = (
                entity.get("entity_id", "unknown") if entity
                else f"unknown:{payload.stream_id}"
            )

            if _is_alert_suppressed(anomaly_type, payload.stream_id, entity_key):
                logger.info(
                    "Alert suppressed (cooldown): %s stream=%s key=%s",
                    anomaly_type, payload.stream_id, entity_key,
                )
            else:
                try:
                    _create_alert_from_anomaly(
                        anomaly=anomaly,
                        entity=entity,
                        zone_id=zone_id,
                        match_data=match_dict,
                        payload=payload,
                        db=db,
                    )
                    _set_alert_cooldown(anomaly_type, payload.stream_id, entity_key)
                    alerts_created += 1
                except Exception as exc:
                    logger.error(
                        "Failed to create alert for anomaly %s: %s",
                        anomaly.get("anomaly_type"),
                        exc,
                        exc_info=True,
                    )

        processed += 1

    # Cache latest detections in Redis for frontend bounding box overlays.
    # TTL=10s — slightly longer than detection interval so the cache stays
    # fresh while the stream is active, and auto-expires when it stops.
    if detection_overlays:
        r = _get_alert_redis()
        if r:
            try:
                import json as _json
                r.set(
                    f"fazri:detections:{payload.stream_id}",
                    _json.dumps(detection_overlays),
                    ex=10,
                )
            except Exception:
                pass  # best-effort cache — preview works without it

    # Update last_event_at on the camera stream record
    cam_stream.last_event_at = datetime.now(timezone.utc)
    db.commit()

    return WebhookProcessedResponse(
        status="ok",
        processed=processed,
        alerts_created=alerts_created,
    )


# ============================================================================
# Stream management
# ============================================================================


@router.post(
    "/streams",
    response_model=StreamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register and start a new camera stream",
)
async def create_stream(
    body: StreamCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
) -> StreamResponse:
    """
    Create a CameraStream DB record, then instruct the DeepFace server to
    start monitoring the RTSP URL.  The webhook URL is constructed from the
    current request's base URL so it works in both local dev and production.
    """
    # Check uniqueness
    existing = (
        db.query(CameraStream)
        .filter(CameraStream.stream_id == body.stream_id)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Stream with stream_id='{body.stream_id}' already exists",
        )

    # Build the webhook URL pointing back at ourselves.
    # Behind a reverse proxy, request.base_url uses the internal http:// scheme.
    # Honour X-Forwarded-Proto so the registered URL uses the public scheme (https).
    base = str(request.base_url).rstrip("/")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    if forwarded_proto:
        # Replace the scheme with whatever the proxy saw (e.g. http → https)
        base = base.replace(f"{request.url.scheme}://", f"{forwarded_proto}://", 1)
    webhook_url = f"{base}/api/v1/deepface/webhook"
    logger.info("Deepface webhook callback URL: %s", webhook_url)

    # Pre-register the stream with go2rtc so the relay is ready for live view /
    # snapshot requests.  DeepFace always connects directly to the camera —
    # go2rtc is only used for browser WebRTC and JPEG snapshots.
    if settings.GO2RTC_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=5) as rtc_client:
                resp = await rtc_client.put(_go2rtc_register_url(body.stream_id, body.rtsp_url))
                if resp.status_code == 200:
                    logger.info("go2rtc stream registered: %s → %s", body.stream_id, body.rtsp_url)
                else:
                    logger.warning("go2rtc stream registration failed (%d): %s", resp.status_code, resp.text)
        except Exception as exc:
            logger.warning("go2rtc unreachable during stream creation: %s", exc)

    # Tell DeepFace server to start monitoring (always direct to camera —
    # the go2rtc relay is unreliable as a DeepFace source because go2rtc
    # uses lazy RTSP connection and may not be ready when DeepFace starts).
    deepface_client = get_deepface_client()
    deepface_stream_id: Optional[str] = None
    error_msg: Optional[str] = None
    stream_status = CameraStreamStatus.ACTIVE

    try:
        df_response = await deepface_client.start_stream(
            stream_id=body.stream_id,
            rtsp_url=body.rtsp_url,  # always direct camera URL
            webhook_url=webhook_url,
        )
        deepface_stream_id = df_response.get("stream_id", body.stream_id)
        logger.info(
            "DeepFace stream started: stream_id=%s deepface_stream_id=%s rtsp=%s",
            body.stream_id, deepface_stream_id, body.rtsp_url,
        )
    except Exception as exc:
        logger.error("Failed to start DeepFace stream %s: %s", body.stream_id, exc)
        stream_status = CameraStreamStatus.ERROR
        error_msg = str(exc)

    # Persist to DB regardless (admin may fix stream later)
    cam_stream = CameraStream(
        stream_id=body.stream_id,
        rtsp_url=body.rtsp_url,
        zone_id=body.zone_id,
        building=body.building,
        floor=body.floor,
        alert_on_unknown_face=body.alert_on_unknown_face,
        status=stream_status,
        deepface_stream_id=deepface_stream_id,
        created_by=current_user.entity_id or current_user.email,
        error_message=error_msg,
    )
    db.add(cam_stream)
    db.commit()
    db.refresh(cam_stream)

    return _stream_to_response(cam_stream)


@router.get(
    "/streams",
    response_model=StreamListResponse,
    summary="List all registered camera streams",
)
async def list_streams(
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> StreamListResponse:
    """Return all camera streams ordered by creation time."""
    streams = db.query(CameraStream).order_by(CameraStream.created_at).all()
    return StreamListResponse(
        streams=[_stream_to_response(s) for s in streams],
        total=len(streams),
    )


@router.patch(
    "/streams/{stream_id}",
    response_model=StreamResponse,
    summary="Update camera stream configuration",
)
async def update_stream(
    stream_id: str,
    body: StreamUpdateRequest,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
) -> StreamResponse:
    """Update mutable fields on a camera stream (zone_id, floor, alert config)."""
    cam_stream = (
        db.query(CameraStream)
        .filter(CameraStream.stream_id == stream_id)
        .first()
    )
    if cam_stream is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream '{stream_id}' not found",
        )

    if body.zone_id is not None:
        cam_stream.zone_id = body.zone_id
    if body.building is not None:
        cam_stream.building = body.building
    if body.floor is not None:
        cam_stream.floor = body.floor
    if body.alert_on_unknown_face is not None:
        cam_stream.alert_on_unknown_face = body.alert_on_unknown_face

    db.commit()
    db.refresh(cam_stream)
    return _stream_to_response(cam_stream)


@router.delete(
    "/streams/{stream_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Stop and remove a camera stream",
)
async def delete_stream(
    stream_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_admin()),
) -> None:
    """Stop DeepFace monitoring for this stream and remove the DB record."""
    cam_stream = (
        db.query(CameraStream)
        .filter(CameraStream.stream_id == stream_id)
        .first()
    )
    if cam_stream is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stream '{stream_id}' not found",
        )

    # Tell DeepFace server to stop
    if cam_stream.status == CameraStreamStatus.ACTIVE:
        deepface_client = get_deepface_client()
        try:
            df_id = cam_stream.deepface_stream_id or stream_id
            await deepface_client.stop_stream(df_id)
        except Exception as exc:
            logger.warning(
                "Could not stop DeepFace stream %s (continuing with DB delete): %s",
                stream_id, exc,
            )

    # Remove go2rtc relay stream
    if settings.GO2RTC_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=5) as rtc_client:
                await rtc_client.delete(
                    f"{settings.GO2RTC_API_URL}/api/streams?src={quote(stream_id, safe='')}",
                )
                logger.info("go2rtc stream removed: %s", stream_id)
        except Exception as exc:
            logger.warning("Could not remove go2rtc stream %s: %s", stream_id, exc)

    db.delete(cam_stream)
    db.commit()


# ============================================================================
# Camera snapshot
# ============================================================================


@router.get(
    "/streams/{stream_id}/snapshot",
    summary="Grab a single JPEG frame from a camera stream",
)
async def get_stream_snapshot(
    stream_id: str,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> StreamingResponse:
    """
    Connects to the RTSP URL of the given stream and returns one JPEG frame.
    Uses a thread executor so the blocking OpenCV call does not stall the event loop.
    Returns HTTP 504 if the camera does not respond within 5 seconds.
    """
    cam_stream = (
        db.query(CameraStream)
        .filter(CameraStream.stream_id == stream_id)
        .first()
    )
    if cam_stream is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Stream '{stream_id}' not found")

    # Use go2rtc's built-in snapshot endpoint if available.
    # This is instant (go2rtc serves the latest decoded frame as JPEG)
    # instead of opening a new RTSP connection per request.
    if settings.GO2RTC_ENABLED:
        try:
            async with httpx.AsyncClient(timeout=8) as rtc_client:
                resp = await rtc_client.get(
                    f"{settings.GO2RTC_API_URL}/api/frame.jpeg",
                    params={"src": stream_id},
                )
                # Auto-register with go2rtc if stream not found, then retry
                if resp.status_code == 404:
                    logger.info("go2rtc stream not found for %s — auto-registering", stream_id)
                    await rtc_client.put(_go2rtc_register_url(stream_id, cam_stream.rtsp_url))
                    resp = await rtc_client.get(
                        f"{settings.GO2RTC_API_URL}/api/frame.jpeg",
                        params={"src": stream_id},
                    )
                resp.raise_for_status()
                return StreamingResponse(io.BytesIO(resp.content), media_type="image/jpeg")
        except Exception as exc:
            logger.warning("go2rtc snapshot failed for %s, falling back to RTSP: %s", stream_id, exc)

    # Fallback: direct RTSP grab (slow — new TCP connection per request)
    loop = asyncio.get_event_loop()
    try:
        jpeg_bytes = await asyncio.wait_for(
            loop.run_in_executor(None, _grab_rtsp_frame, cam_stream.rtsp_url),
            timeout=8.0,
        )
    except (asyncio.TimeoutError, RuntimeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Could not capture a frame from stream '{stream_id}': {exc}",
        )

    return StreamingResponse(io.BytesIO(jpeg_bytes), media_type="image/jpeg")


# ============================================================================
# Live stream proxy (go2rtc MSE via backend)
# ============================================================================


@router.post(
    "/streams/{stream_id}/webrtc",
    summary="WebRTC WHEP signaling proxy for live video",
)
async def webrtc_offer(
    stream_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> Response:
    """
    Proxies WebRTC signaling (WHEP) to go2rtc. The frontend sends an SDP
    offer, this endpoint forwards it to go2rtc and returns the SDP answer.
    Auth happens here (Authorization header); the actual media stream flows
    directly via WebRTC (peer-to-peer, no tokens needed).
    """
    cam_stream = db.query(CameraStream).filter(CameraStream.stream_id == stream_id).first()
    if cam_stream is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Stream '{stream_id}' not found")

    if not settings.GO2RTC_ENABLED:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Live streaming not available")

    # Forward the SDP offer to go2rtc's WHEP endpoint
    body = await request.body()
    content_type = request.headers.get("content-type", "application/sdp")

    try:
        # Longer timeout: go2rtc may need several seconds to connect to the RTSP camera
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{settings.GO2RTC_API_URL}/api/webrtc?src={stream_id}",
                content=body,
                headers={"Content-Type": content_type},
            )

            # If go2rtc doesn't know this stream, register it then wait for
            # it to establish the lazy RTSP connection before retrying WHEP.
            if resp.status_code == 404:
                logger.info("go2rtc stream not found for %s — auto-registering from DB", stream_id)
                reg = await client.put(_go2rtc_register_url(stream_id, cam_stream.rtsp_url))
                if reg.status_code >= 400:
                    logger.error("go2rtc stream registration failed %s: %s %s", stream_id, reg.status_code, reg.text[:200])
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Failed to register stream in go2rtc: {reg.status_code}",
                    )

                # go2rtc connects to the RTSP camera lazily on first consumer.
                # Retry the WHEP offer a few times while it establishes the connection.
                for attempt in range(5):
                    await asyncio.sleep(1.5)
                    resp = await client.post(
                        f"{settings.GO2RTC_API_URL}/api/webrtc?src={stream_id}",
                        content=body,
                        headers={"Content-Type": content_type},
                    )
                    if resp.status_code != 404:
                        break
                    logger.debug("go2rtc WHEP still not ready for %s (attempt %d/5)", stream_id, attempt + 1)

    except httpx.ConnectError:
        logger.error("go2rtc unreachable at %s — is the container running?", settings.GO2RTC_API_URL)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Live streaming service is unavailable. go2rtc is not reachable.",
        )
    except httpx.TimeoutException:
        logger.error("go2rtc timed out for stream %s", stream_id)
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail="Live streaming service timed out.",
        )

    if resp.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"go2rtc WebRTC signaling failed: {resp.status_code} {resp.text[:200]}",
        )

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/sdp"),
    )


# ============================================================================
# Detection overlays (for frontend bounding boxes)
# ============================================================================


@router.get(
    "/streams/{stream_id}/detections",
    summary="Latest face detections for a stream (cached in Redis)",
)
async def get_stream_detections(
    stream_id: str,
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> Dict[str, Any]:
    """
    Returns the most recent face detection results for the given stream,
    including bounding boxes and entity names.  Data is cached in Redis by
    the webhook handler with a 10-second TTL — it's only present while the
    stream is actively producing detections.
    """
    import json as _json

    r = _get_alert_redis()
    if not r:
        return {"detections": [], "cached": False}
    try:
        raw = r.get(f"fazri:detections:{stream_id}")
    except Exception:
        return {"detections": [], "cached": False}
    if not raw:
        return {"detections": [], "cached": False}
    return {"detections": _json.loads(raw), "cached": True}


# ============================================================================
# ONVIF probe
# ============================================================================


@router.post(
    "/onvif/probe",
    summary="Probe an NVR/IP camera via ONVIF to discover channels",
)
async def probe_onvif(
    body: Dict[str, Any],
    current_user: AuthenticatedUser = Depends(require_admin()),
) -> Dict[str, Any]:
    """
    Attempt an ONVIF connection to the given IP camera or NVR.

    Request body:
        { "ip": "192.168.1.64", "port": 80, "username": "admin", "password": "...", "use_https": false }

    Returns on success:
        { "vendor": "Hikvision", "model": "DS-2CD2143G2-I", "channels": [
            { "id": "Profile_1", "name": "MainStream", "rtsp_url": "rtsp://..." }
          ] }

    Returns on failure:
        { "error": "onvif_failed", "message": "..." }
    """
    ip = body.get("ip", "").strip()
    port = int(body.get("port", 80))
    username = body.get("username", "")
    password = body.get("password", "")
    use_https = bool(body.get("use_https", False))

    if not ip:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ip is required")

    loop = asyncio.get_event_loop()
    try:
        result = await asyncio.wait_for(
            loop.run_in_executor(None, _onvif_probe, ip, port, username, password, use_https),
            timeout=15.0,
        )
        return result
    except asyncio.TimeoutError:
        return {"error": "onvif_failed", "message": "Connection timed out — ONVIF may be disabled on this device"}
    except Exception as exc:
        return {"error": "onvif_failed", "message": str(exc)}


def _onvif_probe(ip: str, port: int, username: str, password: str, use_https: bool = False) -> Dict[str, Any]:
    """
    Blocking ONVIF discovery using the onvif-zeep library.

    Strategy:
    1. Try the requested protocol (HTTP or HTTPS).
    2. If a connection-level error occurs (reset, refused, SSL), automatically
       retry with the opposite protocol.
    3. SSL certificate verification is always disabled — NVRs on LANs
       universally use self-signed certificates.
    """
    try:
        from onvif import ONVIFCamera  # type: ignore
    except ImportError:
        raise RuntimeError("onvif-zeep package is not installed — run: pip install onvif-zeep")

    last_error: Optional[Exception] = None
    # Try requested protocol first, then fall back to the opposite
    for https in (use_https, not use_https):
        try:
            result = _onvif_attempt(ip, port, username, password, https)
            result["protocol"] = "https" if https else "http"
            return result
        except (OSError, ConnectionError) as exc:
            last_error = exc
            logger.info(
                "ONVIF %s attempt failed for %s:%d — retrying with %s: %s",
                "HTTPS" if https else "HTTP", ip, port,
                "HTTP" if https else "HTTPS", exc,
            )
            continue
        except Exception as exc:
            # Non-connection errors (auth failure, bad XML, etc.) — don't retry
            raise exc

    raise last_error or RuntimeError("ONVIF probe failed on both HTTP and HTTPS")


def _onvif_attempt(ip: str, port: int, username: str, password: str, use_https: bool) -> Dict[str, Any]:
    """
    Single ONVIF connection attempt.
    Patches requests.Session to disable SSL verification for the duration
    of this call so self-signed NVR certificates are accepted.
    """
    import contextlib
    import requests
    import urllib3
    from onvif import ONVIFCamera  # type: ignore

    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # Temporarily patch requests.Session so every zeep-internal session
    # created by onvif-zeep uses verify=False.
    original_init = requests.Session.__init__

    def _patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.verify = False

    requests.Session.__init__ = _patched_init  # type: ignore[method-assign]
    try:
        cam = ONVIFCamera(ip, port, username, password, encrypt=use_https)
        cam.update_xaddrs()

        # Device info
        device_svc = cam.create_devicemgmt_service()
        info = device_svc.GetDeviceInformation()
        vendor = getattr(info, "Manufacturer", "Unknown")
        model = getattr(info, "Model", "Unknown")

        # Media profiles → stream URIs
        media_svc = cam.create_media_service()
        profiles = media_svc.GetProfiles()

        channels: List[Dict[str, Any]] = []
        for profile in profiles:
            try:
                uri_req = media_svc.create_type("GetStreamUri")
                uri_req.ProfileToken = profile.token
                uri_req.StreamSetup = {
                    "Stream": "RTP-Unicast",
                    "Transport": {"Protocol": "RTSP"},
                }
                uri_resp = media_svc.GetStreamUri(uri_req)
                rtsp_url = uri_resp.Uri
                # Inject percent-encoded credentials into the RTSP URL if not already present
                if username and "://" in rtsp_url and "@" not in rtsp_url:
                    enc_user = requests.utils.quote(username, safe="")
                    enc_pass = requests.utils.quote(password, safe="")
                    rtsp_url = rtsp_url.replace("rtsp://", f"rtsp://{enc_user}:{enc_pass}@")
                channels.append({
                    "id": profile.token,
                    "name": getattr(profile, "Name", profile.token),
                    "rtsp_url": rtsp_url,
                })
            except Exception:
                continue

        return {"vendor": vendor, "model": model, "channels": channels}
    finally:
        requests.Session.__init__ = original_init  # type: ignore[method-assign]


# ============================================================================
# Face registration
# ============================================================================


@router.get(
    "/entities/{entity_id}/registration",
    summary="Check face registration status for an entity",
)
async def get_entity_registration_status(
    entity_id: str,
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> Dict[str, Any]:
    """
    Query the DeepFace pgvector DB for face embeddings where img_name = entity_id.

    Returns:
        {
            "entity_id": str,
            "registered": bool,
            "face_count": int,
            "registered_at": ISO-8601 string | null
        }

    Returns registered=False (not an error) if the DeepFace DB is unreachable or
    the table does not exist yet — frontend should handle this gracefully.
    """
    try:
        conn = psycopg2.connect(settings.DEEPFACE_POSTGRES_URI)
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*), MIN(created_at) FROM face_embeddings WHERE img_name = %s",
                    (entity_id,),
                )
                row = cur.fetchone()
                count = int(row[0]) if row else 0
                registered_at = row[1].isoformat() if (row and row[1]) else None
        return {
            "entity_id": entity_id,
            "registered": count > 0,
            "face_count": count,
            "registered_at": registered_at,
        }
    except Exception as exc:
        logger.warning(
            "Face registration status query failed for entity_id=%s: %s", entity_id, exc
        )
        return {
            "entity_id": entity_id,
            "registered": False,
            "face_count": 0,
            "registered_at": None,
        }


@router.post(
    "/entities/{entity_id}/register",
    response_model=FaceRegistrationResponse,
    summary="Register a face photo for an entity",
)
async def register_face(
    entity_id: str,
    image: UploadFile = File(..., description="Face photo (JPEG or PNG)"),
    current_user: AuthenticatedUser = Depends(require_admin()),
) -> FaceRegistrationResponse:
    """
    Upload a face photo for the given entity_id and register it in the
    DeepFace embedding database using entity_id as the img_name label.

    After this call succeeds, update the user's face_id field via the auth
    service API (fazri-analyzer does not own the Prisma auth DB directly).
    """
    image_data = await image.read()
    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )

    deepface_client = get_deepface_client()
    try:
        result = await deepface_client.register_face(
            entity_id=entity_id,
            image_data=image_data,
            content_type=image.content_type or "image/jpeg",
        )
        logger.info("Face registered for entity_id=%s: %s", entity_id, result)
        return FaceRegistrationResponse(
            entity_id=entity_id,
            registered=True,
            message=f"Face successfully registered for entity '{entity_id}'",
        )
    except Exception as exc:
        logger.error("Face registration failed for entity_id=%s: %s", entity_id, exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"DeepFace server registration failed: {exc}",
        )


# ============================================================================
# Manual face search
# ============================================================================


@router.post(
    "/search",
    response_model=FaceSearchResponse,
    summary="Search for matching faces from an uploaded query image",
)
async def search_face(
    image: UploadFile = File(..., description="Query face image (JPEG or PNG)"),
    current_user: AuthenticatedUser = Depends(require_staff()),
) -> FaceSearchResponse:
    """
    Upload a query face image and return all matching entities enriched with
    their campus entity data from Neo4j.
    """
    image_data = await image.read()
    if not image_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty",
        )

    t_start = time.monotonic()
    deepface_client = get_deepface_client()

    try:
        raw_matches = await deepface_client.search_face(
            image_data=image_data,
            content_type=image.content_type or "image/jpeg",
        )
    except Exception as exc:
        logger.error("Face search failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"DeepFace server search failed: {exc}",
        )

    query_ms = (time.monotonic() - t_start) * 1000
    graph_svc = get_cctv_graph_service()
    results: List[FaceSearchResult] = []

    for m in raw_matches:
        entity_id = m.get("img_name")
        entity = graph_svc.get_entity_by_entity_id(entity_id) if entity_id else None
        results.append(
            FaceSearchResult(
                img_name=entity_id or "unknown",
                entity_id=entity_id,
                entity_name=entity.get("name") if entity else None,
                entity_role=entity.get("role") if entity else None,
                entity_department=entity.get("department") if entity else None,
                distance=m.get("distance", 1.0),
                confidence=m.get("confidence", 0.0),
                threshold=m.get("threshold", settings.DEEPFACE_CONFIDENCE_THRESHOLD),
            )
        )

    return FaceSearchResponse(results=results, query_time_ms=round(query_ms, 2))


# ============================================================================
# Index management
# ============================================================================


@router.post(
    "/index/build",
    summary="Trigger DeepFace ANN index rebuild",
)
async def build_index(
    current_user: AuthenticatedUser = Depends(require_admin()),
) -> Dict[str, Any]:
    """
    Tell the DeepFace server to rebuild its approximate-nearest-neighbour
    search index.  Call after registering a batch of new faces.
    """
    deepface_client = get_deepface_client()
    try:
        result = await deepface_client.build_index()
        logger.info("DeepFace index rebuilt: %s", result)
        return {"status": "ok", "deepface_response": result}
    except Exception as exc:
        logger.error("Index rebuild failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"DeepFace index rebuild failed: {exc}",
        )
