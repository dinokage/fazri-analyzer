"""
InsightFace wrapper — single-pass detection + alignment + embedding.

One call to app.get(frame) returns Face objects with:
  - bbox: [x1, y1, x2, y2] pixel coordinates
  - normed_embedding: 512-dim L2-normalized ArcFace vector
  - det_score: detection confidence (0-1)
  - kps: 5-point facial landmarks

No JPEG encoding, no base64, no TensorFlow.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any

import numpy as np
from insightface.app import FaceAnalysis

from app.config import settings

logger = logging.getLogger(__name__)

# Module-level singleton — initialized by load_engine()
_engine: FaceAnalysis | None = None


def load_engine() -> FaceAnalysis:
    """Load the InsightFace buffalo_l model pack (SCRFD + ArcFace).

    Called once at application startup. Downloads weights on first run
    (~230 MB) and caches them in ~/.insightface/models/.
    """
    global _engine
    det_size = (settings.det_size, settings.det_size)
    _engine = FaceAnalysis(
        name="buffalo_l",
        providers=["CPUExecutionProvider"],
    )
    _engine.prepare(ctx_id=-1, det_size=det_size)
    logger.info(
        "InsightFace engine loaded: buffalo_l (SCRFD + ArcFace), det_size=%s, CPU mode",
        det_size,
    )
    return _engine


def get_engine() -> FaceAnalysis:
    if _engine is None:
        raise RuntimeError("FaceEngine not initialized — call load_engine() at startup")
    return _engine


def detect_and_embed(frame: np.ndarray) -> List[Dict[str, Any]]:
    """Detect all faces in a BGR frame, return embeddings + bounding boxes.

    Each face dict contains:
      bbox: [x1, y1, x2, y2] (int pixel coordinates)
      embedding: np.ndarray(512,) — L2-normalized
      det_score: float (0-1)
      landmarks: list of [x, y] pairs (5-point keypoints)
    """
    engine = get_engine()
    faces = engine.get(frame)

    results = []
    for face in faces:
        x1, y1, x2, y2 = face.bbox.astype(int).tolist()
        results.append({
            "bbox": [x1, y1, x2, y2],
            "embedding": face.normed_embedding,
            "det_score": float(face.det_score),
            "landmarks": face.kps.astype(int).tolist() if face.kps is not None else [],
        })
    return results


def embed_single(frame: np.ndarray) -> Dict[str, Any] | None:
    """Detect and embed a single face in a frame (for registration photos).

    Returns the highest-confidence face, or None if no face detected.
    """
    faces = detect_and_embed(frame)
    if not faces:
        return None
    # Return the face with the highest detection confidence
    return max(faces, key=lambda f: f["det_score"])
