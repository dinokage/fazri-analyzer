"""
RTSP stream processor.

Each StreamProcessor runs as an asyncio Task, reading frames from an RTSP
URL at a configured interval, running InsightFace recognition, and posting
results to a webhook URL.

InsightFace and cv2 calls are blocking/CPU-bound — they run in the default
thread executor via loop.run_in_executor() to avoid blocking the event loop.
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import cv2
import httpx
import numpy as np

from urllib.parse import urlparse, urlunparse

from app.config import settings

logger = logging.getLogger(__name__)


def _redact_rtsp_url(url: str) -> str:
    """Strip userinfo (username:password@) from an RTSP URL for safe logging."""
    parsed = urlparse(url)
    if parsed.username or parsed.password:
        redacted = parsed._replace(netloc=f"{parsed.hostname}:{parsed.port}" if parsed.port else parsed.hostname)
        return urlunparse(redacted)
    return url

# Global registry: stream_id → StreamProcessor
_streams: Dict[str, "StreamProcessor"] = {}


def get_all_streams() -> List["StreamProcessor"]:
    return list(_streams.values())


def get_stream(stream_id: str) -> Optional["StreamProcessor"]:
    return _streams.get(stream_id)


async def start_stream(
    rtsp_url: str,
    interval_seconds: float,
    webhook_url: str,
    stream_id: Optional[str] = None,
) -> "StreamProcessor":
    sid = stream_id or str(uuid.uuid4())[:8]
    if sid in _streams:
        raise ValueError(f"Stream '{sid}' is already running.")
    processor = StreamProcessor(sid, rtsp_url, interval_seconds, webhook_url)
    await processor.start()
    _streams[sid] = processor
    return processor


async def stop_stream(stream_id: str) -> "StreamProcessor":
    processor = _streams.get(stream_id)
    if not processor:
        raise KeyError(f"Stream '{stream_id}' not found.")
    await processor.stop()
    return processor


class StreamProcessor:
    def __init__(
        self,
        stream_id: str,
        rtsp_url: str,
        interval_seconds: float,
        webhook_url: str,
    ) -> None:
        self.stream_id = stream_id
        self.rtsp_url = rtsp_url
        self.interval_seconds = interval_seconds
        self.webhook_url = webhook_url
        self.running = False
        self.frames_processed = 0
        self.started_at: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self._task: Optional[asyncio.Task] = None
        # Per-stream face tracker: maps tracker_id → {embedding, last_seen}
        self._face_tracker: Dict[str, Dict] = {}

    @property
    def status(self) -> str:
        if self.last_error and not self.running:
            return "error"
        return "running" if self.running else "stopped"

    async def start(self) -> None:
        self.running = True
        self.started_at = datetime.now(timezone.utc)
        self._task = asyncio.create_task(self._loop(), name=f"stream-{self.stream_id}")
        logger.info("Stream %s started: %s (every %.1fs)", self.stream_id, _redact_rtsp_url(self.rtsp_url), self.interval_seconds)

    async def stop(self) -> None:
        self.running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        _streams.pop(self.stream_id, None)
        logger.info("Stream %s stopped.", self.stream_id)

    # ── Internal loop ──────────────────────────────────────────────────────────

    async def _loop(self) -> None:
        loop = asyncio.get_event_loop()
        cap: Optional[cv2.VideoCapture] = None

        try:
            cap = await self._open_capture(loop)

            while self.running:
                ret, frame = await loop.run_in_executor(None, self._read_latest_frame, cap)

                if not ret or frame is None:
                    logger.warning("Stream %s: failed to read frame, reconnecting in 5s...", self.stream_id)
                    self.last_error = "Frame read failed — attempting reconnect"
                    await loop.run_in_executor(None, cap.release)
                    await asyncio.sleep(5)
                    cap = await self._open_capture(loop)
                    continue

                self.last_error = None
                await self._process_frame(loop, frame)
                self.frames_processed += 1
                await asyncio.sleep(self.interval_seconds)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            self.last_error = str(exc)
            self.running = False
            logger.exception("Stream %s crashed: %s", self.stream_id, exc)
        finally:
            if cap is not None:
                await loop.run_in_executor(None, cap.release)

    @staticmethod
    def _read_latest_frame(cap: cv2.VideoCapture) -> tuple:
        """Flush the RTSP buffer and return the most recent frame."""
        ret = False
        for _ in range(30):
            ret = cap.grab()
            if not ret:
                break
        if not ret:
            return False, None
        ret, frame = cap.retrieve()
        return ret, frame

    async def _open_capture(self, loop: asyncio.AbstractEventLoop) -> cv2.VideoCapture:
        def _open():
            import os
            cv2.setLogLevel(0)
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        cap = await loop.run_in_executor(None, _open)
        if not cap.isOpened():
            raise ConnectionError(f"Cannot open RTSP stream: {_redact_rtsp_url(self.rtsp_url)}")
        logger.info("Stream %s: connected to %s", self.stream_id, _redact_rtsp_url(self.rtsp_url))
        return cap

    # ── Face tracker ───────────────────────────────────────────────────────────

    def _resolve_tracker_id(self, embedding: list) -> str:
        """Match an embedding against tracked unknown faces via cosine similarity."""
        now = time.monotonic()

        # Prune stale entries
        ttl = settings.face_track_ttl
        self._face_tracker = {
            tid: data for tid, data in self._face_tracker.items()
            if now - data["last_seen"] < ttl
        }

        emb = np.array(embedding, dtype=np.float32)
        emb_norm = emb / (np.linalg.norm(emb) + 1e-10)

        best_tid, best_sim = None, 0.0
        for tid, data in self._face_tracker.items():
            stored = np.array(data["embedding"], dtype=np.float32)
            stored_norm = stored / (np.linalg.norm(stored) + 1e-10)
            sim = float(np.dot(emb_norm, stored_norm))
            if sim > best_sim:
                best_sim = sim
                best_tid = tid

        if best_tid and best_sim >= settings.face_track_similarity:
            self._face_tracker[best_tid]["last_seen"] = now
            return best_tid

        new_tid = str(uuid.uuid4())[:12]
        self._face_tracker[new_tid] = {"embedding": embedding, "last_seen": now}
        logger.debug(
            "Stream %s: new unknown face tracked as %s (best sim: %.3f)",
            self.stream_id, new_tid, best_sim,
        )
        return new_tid

    # ── Frame processing ───────────────────────────────────────────────────────

    async def _process_frame(self, loop: asyncio.AbstractEventLoop, frame: np.ndarray) -> None:
        from app.face_engine import detect_and_embed
        from app.pgvector_service import get_pgvector_service

        # ONE call: detect all faces + compute all embeddings (no JPEG encoding)
        faces = await loop.run_in_executor(None, detect_and_embed, frame)
        if not faces:
            return

        pgvector = get_pgvector_service()
        threshold = settings.cosine_threshold
        matches = []

        for face in faces:
            bbox = face["bbox"]  # [x1, y1, x2, y2]
            embedding = face["embedding"]
            det_score = face["det_score"]

            # Search pgvector for closest match (HNSW indexed, sub-ms)
            results = await loop.run_in_executor(
                None, pgvector.search, embedding, threshold,
            )

            facial_area = {
                "x": bbox[0],
                "y": bbox[1],
                "w": bbox[2] - bbox[0],
                "h": bbox[3] - bbox[1],
            }

            if results:
                best = results[0]
                matches.append({
                    "img_name": best["identity_name"],
                    "distance": round(best["distance"], 4),
                    "confidence": round(det_score * 100, 2),
                    "threshold": threshold,
                    "facial_area": facial_area,
                })
            else:
                tracker_id = self._resolve_tracker_id(embedding.tolist())
                matches.append({
                    "img_name": "UNKNOWN_FACE",
                    "distance": 1.0,
                    "confidence": round(det_score * 100, 2),
                    "threshold": threshold,
                    "tracker_id": tracker_id,
                    "facial_area": facial_area,
                })

        if matches:
            await self._post_webhook(matches)

    # ── Webhook delivery ───────────────────────────────────────────────────────

    async def _post_webhook(self, matches: list) -> None:
        import hashlib
        import hmac
        import json as _json

        payload = {
            "stream_id": self.stream_id,
            "rtsp_url": _redact_rtsp_url(self.rtsp_url),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "frames_processed": self.frames_processed,
            "faces_found": len(matches),
            "matches": matches,
        }
        body = _json.dumps(payload).encode()

        headers = {"Content-Type": "application/json"}
        if settings.deepface_webhook_secret:
            sig = hmac.new(settings.deepface_webhook_secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-DeepFace-Signature"] = f"sha256={sig}"

        try:
            async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
                resp = await client.post(self.webhook_url, content=body, headers=headers)
                logger.debug(
                    "Stream %s webhook → %s [%d]",
                    self.stream_id, self.webhook_url, resp.status_code,
                )
        except Exception as exc:
            logger.warning("Stream %s webhook failed: %s", self.stream_id, exc)
