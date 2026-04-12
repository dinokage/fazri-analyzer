"""
Face embedding namespace helpers for multi-tenant DeepFace.

Face labels in DeepFace are namespaced as: {org_id}/{entity_id}
The `/` separator is used because it is illegal in both Better Auth
org IDs (CUIDs) and FAZRI entity IDs (alphanumeric + underscore).
"""

from __future__ import annotations
from typing import Tuple


def build_namespaced_face_id(org_id: str, entity_id: str) -> str:
    """Build a namespaced face label for DeepFace storage."""
    return f"{org_id}/{entity_id}"


def parse_namespaced_face_id(namespaced_id: str) -> Tuple[str, str]:
    """
    Parse a namespaced face label back to (org_id, entity_id).

    Returns ("", original_id) for legacy un-namespaced labels.
    """
    parts = namespaced_id.split("/", 1)
    if len(parts) == 2:
        return parts[0], parts[1]
    return "", namespaced_id
