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
            cv2.setLogLevel(0)  # suppress H264 decode warnings from FFmpeg
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            return cap

        cap = await loop.run_in_executor(None, _open)
        if not cap.isOpened():
            raise ConnectionError(f"Cannot open RTSP stream: {self.rtsp_url}")
        logger.info("Stream %s: connected to %s", self.stream_id, self.rtsp_url)
        return cap

    async def _process_frame(self, loop: asyncio.AbstractEventLoop, frame: np.ndarray) -> None:
        from deepface import DeepFace
        from deepface.modules.exceptions import EmptyDatasource, FaceNotDetected

        # Encode frame as JPEG data-URI
        _, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        data_uri = "data:image/jpeg;base64," + base64.b64encode(buffer).decode()

        # Run DeepFace search in thread executor
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
                    normalization=settings.normalization,
                    l2_normalize=settings.l2_normalize,
                    database_type="postgres",
                    connection_details=settings.connection_details,
                ),
            )
        except (FaceNotDetected, EmptyDatasource):
            return
        except Exception as exc:
            logger.debug("Stream %s search error: %s", self.stream_id, exc)
            return

        # Collect matches across all detected faces
        matches = []
        for df in dfs:
            if df.empty:
                continue
            for _, row in df.iterrows():
                distance = row.get("distance")
                threshold = row.get("threshold")
                # Compute recognition confidence from distance/threshold.
                # DeepFace's "confidence" column is the face detector probability,
                # not how well the face matched the registered identity.
                recognition_confidence = (
                    round((1 - distance / threshold) * 100, 2)
                    if distance is not None and threshold
                    else None
                )
                matches.append({
                    "img_name": row.get("img_name"),
                    "distance": distance,
                    "threshold": threshold,
                    "detector_confidence": row.get("confidence"),
                    "recognition_confidence": recognition_confidence,
                    "facial_area": {
                        "x": row.get("target_x"),
                        "y": row.get("target_y"),
                        "w": row.get("target_w"),
                        "h": row.get("target_h"),
                    },
                })

        if not matches:
            return

        await self._post_webhook(matches)

    async def _post_webhook(self, matches: list) -> None:
        payload = {
            "stream_id": self.stream_id,
            "rtsp_url": self.rtsp_url,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "frames_processed": self.frames_processed,
            "faces_found": len(matches),
            "matches": matches,
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(self.webhook_url, json=payload)
                logger.debug(
                    "Stream %s webhook → %s [%d]",
                    self.stream_id, self.webhook_url, resp.status_code,
                )
        except Exception as exc:
            logger.warning("Stream %s webhook failed: %s", self.stream_id, exc)
