"""
DeepFace Server HTTP Client.

Wraps every outbound HTTP call to the external DeepFace server.
Uses a module-level singleton so a single httpx.AsyncClient (with connection
pooling) is shared across all requests for the lifetime of the application.

Usage:
    from services.deepface_client import get_deepface_client

    client = get_deepface_client()
    result = await client.register_face("entity_abc", image_bytes, "image/jpeg")
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx

from config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_deepface_client: Optional["DeepFaceClient"] = None


def get_deepface_client() -> "DeepFaceClient":
    """Return (or lazily create) the module-level DeepFaceClient singleton."""
    global _deepface_client
    if _deepface_client is None:
        _deepface_client = DeepFaceClient(base_url=settings.DEEPFACE_SERVER_URL)
        logger.info("DeepFaceClient initialised — base_url=%s", settings.DEEPFACE_SERVER_URL)
    return _deepface_client


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class DeepFaceClient:
    """
    Async HTTP client for the DeepFace server REST API.

    All methods raise httpx.HTTPStatusError on non-2xx responses so callers
    can handle errors explicitly.  A 30-second timeout is applied globally.
    """

    _TIMEOUT = 30.0  # seconds

    def __init__(self, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._TIMEOUT,
        )

    # ------------------------------------------------------------------
    # Face management
    # ------------------------------------------------------------------

    async def register_face(
        self,
        entity_id: str,
        image_data: bytes,
        content_type: str = "image/jpeg",
    ) -> Dict[str, Any]:
        """
        Register a face embedding in the DeepFace database.

        Args:
            entity_id: Used as the img_name label — must equal the entity's
                       entity_id so webhook matches can be resolved back.
            image_data: Raw image bytes (JPEG or PNG).
            content_type: MIME type of the image.

        Returns:
            DeepFace server JSON response (e.g. {"result": "success", ...}).
        """
        files = {
            "img": (f"{entity_id}.jpg", image_data, content_type),
        }
        data = {"img_name": entity_id}

        logger.debug("Registering face for entity_id=%s", entity_id)
        response = await self._client.post("/register", files=files, data=data)
        response.raise_for_status()
        return response.json()

    async def search_face(self, image_data: bytes, content_type: str = "image/jpeg") -> List[Dict[str, Any]]:
        """
        Search for matching faces in the DeepFace database.

        Args:
            image_data: Raw query image bytes.
            content_type: MIME type of the image.

        Returns:
            List of match dicts, each containing img_name, distance, confidence, threshold.
        """
        files = {"img": ("query.jpg", image_data, content_type)}

        logger.debug("Searching faces")
        response = await self._client.post("/search", files=files)
        response.raise_for_status()
        payload = response.json()
        # DeepFace may return {"results": [...]} or a bare list depending on version
        if isinstance(payload, list):
            return payload
        return payload.get("results", payload.get("matches", []))

    async def detect_faces(
        self, image_data: bytes, content_type: str = "image/jpeg"
    ) -> List[Dict[str, Any]]:
        """
        Detect face bounding boxes and crops in an image (no identity match).

        Returns:
            List of detection dicts with facial_area, confidence, etc.
        """
        files = {"img": ("detect.jpg", image_data, content_type)}

        response = await self._client.post("/detect", files=files)
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("detections", [])

    # ------------------------------------------------------------------
    # Stream management
    # ------------------------------------------------------------------

    async def start_stream(
        self,
        stream_id: str,
        rtsp_url: str,
        webhook_url: str,
    ) -> Dict[str, Any]:
        """
        Instruct the DeepFace server to start monitoring an RTSP stream.

        Args:
            stream_id: Unique label for this stream.
            rtsp_url: Full RTSP URL (e.g. rtsp://admin:pass@192.168.1.10/stream).
            webhook_url: Full URL of our webhook receiver endpoint.

        Returns:
            DeepFace response dict (e.g. {"stream_id": ..., "status": "started"}).
        """
        body = {
            "stream_id": stream_id,
            "rtsp_url": rtsp_url,
            "webhook_url": webhook_url,
        }
        logger.info("Starting stream stream_id=%s rtsp=%s", stream_id, rtsp_url)
        response = await self._client.post("/stream/start", json=body)
        response.raise_for_status()
        return response.json()

    async def stop_stream(self, stream_id: str) -> Dict[str, Any]:
        """
        Instruct the DeepFace server to stop monitoring a stream.

        Args:
            stream_id: The stream label that was used at start time.
        """
        logger.info("Stopping stream stream_id=%s", stream_id)
        response = await self._client.post(f"/stream/stop/{stream_id}")
        response.raise_for_status()
        return response.json()

    async def list_streams(self) -> List[Dict[str, Any]]:
        """Return the list of streams currently active on the DeepFace server."""
        response = await self._client.get("/stream/status")
        response.raise_for_status()
        payload = response.json()
        if isinstance(payload, list):
            return payload
        return payload.get("streams", [])

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    async def build_index(self) -> Dict[str, Any]:
        """
        Trigger the DeepFace server to rebuild its ANN search index.

        Call this after bulk face registrations so that new embeddings
        are searchable immediately.
        """
        logger.info("Triggering DeepFace index rebuild")
        response = await self._client.post("/build-index")
        response.raise_for_status()
        return response.json()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def aclose(self) -> None:
        """Close the underlying httpx client (call on app shutdown)."""
        await self._client.aclose()
