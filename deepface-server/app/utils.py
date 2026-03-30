"""
Image I/O and serialisation helpers shared across routes.
"""
from __future__ import annotations

import base64
import io
import math
from typing import Optional

import numpy as np
from fastapi import UploadFile
from PIL import Image


async def load_image_input(
    file: Optional[UploadFile],
    base64_str: Optional[str],
) -> str:
    """
    Normalise the two accepted input forms into a data-URI string that
    DeepFace accepts as img_path.
    """
    if file is not None:
        raw = await file.read()
        encoded = base64.b64encode(raw).decode("utf-8")
        mime = _mime_from_bytes(raw)
        return f"data:{mime};base64,{encoded}"

    if base64_str is not None:
        if base64_str.startswith("data:"):
            return base64_str
        # Raw base64 without a prefix — assume JPEG
        return f"data:image/jpeg;base64,{base64_str}"

    raise ValueError("Either 'file' (multipart) or 'image' (base64) must be provided")


def _mime_from_bytes(data: bytes) -> str:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"  # safe fallback


def ndarray_to_base64_png(face_array: np.ndarray) -> str:
    """
    Convert a DeepFace face crop (float32, RGB, values in [0,1]) to a
    base64-encoded PNG string.

    DeepFace.extract_faces() with normalize_face=True returns float32 arrays
    already divided by 255. We scale back to uint8 before PIL encoding.
    """
    arr = (face_array * 255).clip(0, 255).astype(np.uint8)
    img = Image.fromarray(arr, mode="RGB")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def sanitise_nan(value):
    """Recursively replace float NaN with None for JSON serialisation."""
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, dict):
        return {k: sanitise_nan(v) for k, v in value.items()}
    if isinstance(value, list):
        return [sanitise_nan(v) for v in value]
    return value


def df_to_search_matches(df) -> list[dict]:
    """
    Convert a pandas DataFrame returned by DeepFace.search() to a list of
    plain dicts, with NaN replaced by None.
    """
    records = df.to_dict(orient="records")
    return [sanitise_nan(r) for r in records]
