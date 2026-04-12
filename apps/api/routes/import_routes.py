"""
Data import API routes.

POST /api/v1/import/sap-csv  — Import entity master data from a SAP CSV file upload.
"""

from __future__ import annotations

import io
import logging
import os
import tempfile
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from auth.dependencies import require_admin, require_org_admin
from auth.models import AuthenticatedUser
from database.connection import get_db

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/import", tags=["import"])


class ImportResult(BaseModel):
    created: int
    updated: int
    skipped: int
    errors: int
    error_messages: List[str] = []


@router.post(
    "/sap-csv",
    response_model=ImportResult,
    summary="Import entity master data from SAP CSV export",
    description=(
        "Accepts a multipart CSV file upload and upserts entity_profiles "
        "and entity_identifiers records.  Admin-only.  Safe to run multiple times."
    ),
)
async def import_sap_csv(
    file: UploadFile = File(..., description="SAP CSV export file"),
    db: Session = Depends(get_db),
    current_user: AuthenticatedUser = Depends(require_org_admin),
) -> ImportResult:
    """
    Read a SAP CSV upload and import entity profiles into PostgreSQL.

    Expected CSV columns (at minimum):
        entity_id, name, role, email, department,
        student_id, staff_id, card_id, device_hash, face_id

    Returns created / updated / skipped counts.
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="File must be a .csv file",
        )

    # Stream the upload into a temp file to avoid buffering the entire file in memory
    _CHUNK = 64 * 1024  # 64 KB
    first_chunk = await file.read(_CHUNK)
    if not first_chunk:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Uploaded file is empty",
        )

    tmp_path: Optional[str] = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", suffix=".csv", delete=False
        ) as tmp:
            tmp.write(first_chunk)
            while True:
                chunk = await file.read(_CHUNK)
                if not chunk:
                    break
                tmp.write(chunk)
            tmp_path = tmp.name

        from services.entity_resolution_service import get_entity_resolution_service

        svc = get_entity_resolution_service()
        stats = svc.bulk_import_from_csv(tmp_path, db=db)

        logger.info(
            "SAP CSV import by user=%s: created=%d updated=%d skipped=%d",
            getattr(current_user, "sub", "unknown"),
            stats["created"],
            stats["updated"],
            stats["skipped"],
        )

        return ImportResult(
            created=stats["created"],
            updated=stats["updated"],
            skipped=stats["skipped"],
            errors=0,
        )

    except Exception as exc:
        logger.error("SAP CSV import failed: %s", exc, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Import failed",
        ) from exc
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)
