"""
RTSP stream processor.

Each StreamProcessor runs as an asyncio Task, reading frames from an RTSP
URL at a configured interval, running DeepFace recognition, and posting
results to a webhook URL.

DeepFace and cv2 calls are blocking/CPU-bound — they run in the default
thread executor via loop.run_in_executor() to avoid blocking the event loop.
"""
from __future__ import annotations

import asyncio
import base64
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

import cv2
import httpx
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

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
    _streams[sid] = processor
    await processor.start()
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
        # Used to assign stable IDs to unknown faces across consecutive frames.
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
        logger.info("Stream %s started: %s (every %.1fs)", self.stream_id, self.rtsp_url, self.interval_seconds)

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
        """Flush the RTSP buffer and return the most recent frame.

        OpenCV buffers incoming RTSP frames. If we sleep between reads, the
        buffer fills up and cap.read() returns stale frames. Calling grab()
        repeatedly drains the buffer; retrieve() decodes only the last one.
        """
        ret = False
        for _ in range(30):  # drain up to ~1 s of buffered frames at 30 fps
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
            cv2.setLogLevel(0)  # suppress H264 decode warnings from FFmpeg
            # Force TCP transport so OpenCV's FFmpeg backend doesn't use UDP.
            # UDP drops/reorders packets over Tailscale, causing H264 decode errors.
            # OPENCV_FFMPEG_CAPTURE_OPTIONS is the correct way — URL query params
            # are not honoured by OpenCV's FFmpeg backend.
            os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        cap = await loop.run_in_executor(None, _open)
        if not cap.isOpened():
            raise ConnectionError(f"Cannot open RTSP stream: {self.rtsp_url}")
        logger.info("Stream %s: connected to %s", self.stream_id, self.rtsp_url)
        return cap

    def _resolve_tracker_id(self, embedding: list) -> str:
        """Match an embedding against tracked unknown faces via cosine similarity.

        Returns an existing tracker_id if the face is recognised, or generates
        a new one.  Stale entries (older than face_track_ttl) are pruned each call.
        """
        now = time.monotonic()

        # Prune stale entries
        ttl = settings.face_track_ttl
        self._face_tracker = {
            tid: data for tid, data in self._face_tracker.items()
            if now - data["last_seen"] < ttl
        }

        # Cosine similarity against all tracked embeddings
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

        # New face — assign a fresh tracker_id
        new_tid = str(uuid.uuid4())[:12]
        self._face_tracker[new_tid] = {"embedding": embedding, "last_seen": now}
        logger.debug(
            "Stream %s: new unknown face tracked as %s (similarity to best existing: %.3f)",
            self.stream_id, new_tid, best_sim,
        )
        return new_tid

    async def _process_frame(self, loop: asyncio.AbstractEventLoop, frame: np.ndarray) -> None:
        from deepface import DeepFace
        from deepface.modules.exceptions import EmptyDatasource, FaceNotDetected

        # Encode frame as JPEG data-URI
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, settings.jpeg_quality])
        data_uri = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()

        # Run DeepFace search in thread executor.
        # similarity_search=True bypasses DeepFace's hardcoded internal threshold
        # (0.55 for Buffalo_L) so we can apply our own configurable threshold.
        # k=1 returns only the best match per face to reduce payload size.
        try:
            dfs = await loop.run_in_executor(
                None,
                lambda: DeepFace.search(
                    img=data_uri,
                    model_name=settings.model_name,
                    detector_backend=settings.detector_backend,
                    distance_metric=settings.distance_metric,
                    enforce_detection=False,  # frames won't always contain a face
                    align=True,
                    expand_percentage=settings.expand_percentage,
                    normalization=settings.normalization,
                    l2_normalize=settings.l2_normalize,
                    similarity_search=True,   # skip internal threshold filter
                    k=1,                      # best match per face only
                    database_type="postgres",
                    connection_details=settings.connection_details,
                ),
            )
        except (FaceNotDetected, EmptyDatasource):
            return
        except Exception as exc:
            err = str(exc)
            # "No embeddings found in the database" means pgvector is empty.
            # DeepFace raises a plain Exception (not EmptyDatasource) for this.
            # Fall back to face detection only so we can still alert on unknown faces.
            if "No embeddings found in the database" in err:
                await self._handle_empty_database(loop, data_uri)
            else:
                logger.warning("Stream %s DeepFace error (skipping frame): %s", self.stream_id, exc)
            return

        # Collect matches across all detected faces.
        # dfs is a list with one DataFrame per detected face in the frame.
        # Since we use similarity_search=True, DataFrames may contain rows
        # that exceed our threshold — we apply our own filter here.
        # An empty DataFrame means a face was detected but the pgvector DB
        # had no embeddings at all (different from "match exists but too distant").
        threshold = settings.cosine_threshold
        matches = []
        unknown_match_indices: List[tuple] = []  # (dfs_index, matches_index)

        for i, df in enumerate(dfs):
            if df.empty:
                # No embeddings in DB for this face
                unknown_match_indices.append((i, len(matches)))
                matches.append({
                    "img_name": "UNKNOWN_FACE",
                    "distance": 1.0,
                    "confidence": 0.0,
                    "threshold": threshold,
                    "facial_area": {"x": 0, "y": 0, "w": 0, "h": 0},
                })
                continue

            # Apply our own threshold: best match (k=1) must be within threshold.
            # Pandas returns numpy types (int64, float64) which are not JSON
            # serializable — cast everything to native Python types.
            best_row = df.iloc[0] if len(df) > 0 else None
            if best_row is None or float(best_row.get("distance", 1.0)) > threshold:
                # Face detected but no match within our threshold → unknown
                unknown_match_indices.append((i, len(matches)))
                matches.append({
                    "img_name": "UNKNOWN_FACE",
                    "distance": float(best_row.get("distance", 1.0)) if best_row is not None else 1.0,
                    "confidence": float(best_row.get("confidence", 0.0)) if best_row is not None else 0.0,
                    "threshold": threshold,
                    "facial_area": {
                        "x": int(best_row.get("target_x", 0) or 0) if best_row is not None else 0,
                        "y": int(best_row.get("target_y", 0) or 0) if best_row is not None else 0,
                        "w": int(best_row.get("target_w", 0) or 0) if best_row is not None else 0,
                        "h": int(best_row.get("target_h", 0) or 0) if best_row is not None else 0,
                    },
                })
                continue

            matches.append({
                "img_name": str(best_row.get("img_name")),
                "distance": float(best_row.get("distance")),
                "confidence": float(best_row.get("confidence", 0.0)),
                "threshold": threshold,
                "facial_area": {
                    "x": int(best_row.get("target_x") or 0),
                    "y": int(best_row.get("target_y") or 0),
                    "w": int(best_row.get("target_w") or 0),
                    "h": int(best_row.get("target_h") or 0),
                },
            })

        if not matches:
            return

        # For unknown faces, compute embeddings via represent() to assign
        # stable tracker_ids.  represent() uses the same detector on the
        # same image, so results are 1:1 ordered with the search() DataFrames.
        if unknown_match_indices:
            try:
                face_objs = await loop.run_in_executor(
                    None,
                    lambda: DeepFace.represent(
                        img_path=data_uri,
                        model_name=settings.model_name,
                        detector_backend=settings.detector_backend,
                        enforce_detection=False,
                        align=True,
                        expand_percentage=settings.expand_percentage,
                        normalization=settings.normalization,
                        l2_normalize=settings.l2_normalize,
                    ),
                )
                for dfs_idx, match_idx in unknown_match_indices:
                    if dfs_idx < len(face_objs):
                        fobj = face_objs[dfs_idx]
                        embedding = fobj.get("embedding", [])
                        area = fobj.get("facial_area", {})
                        if embedding:
                            tracker_id = self._resolve_tracker_id(embedding)
                            matches[match_idx]["tracker_id"] = tracker_id
                        matches[match_idx]["facial_area"] = {
                            "x": area.get("x", 0),
                            "y": area.get("y", 0),
                            "w": area.get("w", 0),
                            "h": area.get("h", 0),
                        }
            except Exception as exc:
                logger.debug("Stream %s: represent() for tracking failed: %s", self.stream_id, exc)

        await self._post_webhook(matches)

    async def _handle_empty_database(
        self, loop: asyncio.AbstractEventLoop, data_uri: str
    ) -> None:
        """
        Called when pgvector has no registered embeddings.
        Runs face detection only (no search) so we can still post UNKNOWN_FACE
        entries and trigger the alert_on_unknown_face rule on the backend.
        """
        from deepface import DeepFace
        from deepface.modules.exceptions import FaceNotDetected

        try:
            faces = await loop.run_in_executor(
                None,
                lambda: DeepFace.extract_faces(
                    img_path=data_uri,
                    detector_backend=settings.detector_backend,
                    enforce_detection=True,
                    align=True,
                ),
            )
        except FaceNotDetected:
            return  # No face in frame — nothing to report
        except Exception as exc:
            logger.debug("Stream %s face detection error: %s", self.stream_id, exc)
            return

        if not faces:
            return

        # Get embeddings for tracker_id assignment.
        # represent() is used instead of extract_faces() because it returns
        # the face embedding alongside coordinates.
        face_objs: list = []
        try:
            from deepface import DeepFace as _DF
            face_objs = await loop.run_in_executor(
                None,
                lambda: _DF.represent(
                    img_path=data_uri,
                    model_name=settings.model_name,
                    detector_backend=settings.detector_backend,
                    enforce_detection=False,
                    align=True,
                    expand_percentage=settings.expand_percentage,
                    normalization=settings.normalization,
                    l2_normalize=settings.l2_normalize,
                ),
            )
        except Exception as exc:
            logger.debug("Stream %s: represent() for empty-db tracking failed: %s", self.stream_id, exc)

        matches = []
        for i, face in enumerate(faces):
            area = face.get("facial_area", {})
            tracker_id = None
            if i < len(face_objs):
                embedding = face_objs[i].get("embedding", [])
                if embedding:
                    tracker_id = self._resolve_tracker_id(embedding)
            matches.append({
                "img_name": "UNKNOWN_FACE",
                "distance": 1.0,
                "confidence": round(face.get("confidence", 0.0) * 100, 2),
                "threshold": 0.40,
                "facial_area": {
                    "x": area.get("x", 0),
                    "y": area.get("y", 0),
                    "w": area.get("w", 0),
                    "h": area.get("h", 0),
                },
                "tracker_id": tracker_id,
            })

        logger.info(
            "Stream %s: database empty, detected %d unknown face(s)",
            self.stream_id, len(matches),
        )
        await self._post_webhook(matches)

    async def _post_webhook(self, matches: list) -> None:
        import hashlib
        import hmac
        import json as _json

        payload = {
            "stream_id": self.stream_id,
            "rtsp_url": self.rtsp_url,
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
