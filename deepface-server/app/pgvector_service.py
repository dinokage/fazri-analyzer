"""
Direct pgvector operations for face embedding storage and search.

Uses psycopg v3 + pgvector extension for HNSW-indexed cosine similarity
search. No DeepFace, no pandas — raw SQL for maximum performance.
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from app.config import settings

logger = logging.getLogger(__name__)


class PgVectorService:
    """Face embedding CRUD with HNSW-indexed cosine search."""

    def __init__(self, connection_uri: Optional[str] = None):
        self.uri = connection_uri or settings.deepface_postgres_uri

    def _connect(self) -> psycopg.Connection:
        conn = psycopg.connect(self.uri)
        register_vector(conn)
        return conn

    def ensure_schema(self) -> None:
        """Create the face_embeddings table + HNSW index if they don't exist."""
        with self._connect() as conn:
            conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
            conn.execute("""
                CREATE TABLE IF NOT EXISTS face_embeddings (
                    id BIGSERIAL PRIMARY KEY,
                    identity_name TEXT NOT NULL,
                    embedding vector(512) NOT NULL,
                    det_score FLOAT DEFAULT 0,
                    created_at TIMESTAMPTZ DEFAULT now()
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS face_embeddings_hnsw
                ON face_embeddings
                USING hnsw (embedding vector_cosine_ops)
                WITH (m = 16, ef_construction = 128)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS face_embeddings_identity
                ON face_embeddings (identity_name)
            """)
            conn.commit()
        logger.info("pgvector schema ensured (face_embeddings + HNSW index)")

    def register(
        self,
        identity_name: str,
        embedding: np.ndarray,
        det_score: float = 0.0,
    ) -> int:
        """Insert one face embedding. Call multiple times for multi-shot registration.

        Returns the row ID.
        """
        with self._connect() as conn:
            row = conn.execute(
                """
                INSERT INTO face_embeddings (identity_name, embedding, det_score)
                VALUES (%s, %s, %s)
                RETURNING id
                """,
                (identity_name, embedding, det_score),
            ).fetchone()
            conn.commit()
            return row[0]

    def search(
        self,
        embedding: np.ndarray,
        threshold: float = 0.55,
        limit: int = 1,
    ) -> List[Dict[str, Any]]:
        """Cosine distance search via HNSW index.

        pgvector's <=> operator returns cosine DISTANCE (0 = identical, 2 = opposite).
        threshold: maximum cosine distance to consider a match.
        Returns matches sorted by distance (closest first).
        """
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT identity_name, embedding <=> %s AS distance
                FROM face_embeddings
                WHERE embedding <=> %s < %s
                ORDER BY distance ASC
                LIMIT %s
                """,
                (embedding, embedding, threshold, limit),
            ).fetchall()
            return [
                {"identity_name": r[0], "distance": float(r[1])}
                for r in rows
            ]

    def delete_by_name(self, identity_name: str) -> int:
        """Delete all embeddings for a person. Returns count of deleted rows."""
        with self._connect() as conn:
            result = conn.execute(
                "DELETE FROM face_embeddings WHERE identity_name = %s",
                (identity_name,),
            )
            conn.commit()
            return result.rowcount

    def count_by_name(self, identity_name: str) -> int:
        """Count how many embeddings exist for a person."""
        with self._connect() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM face_embeddings WHERE identity_name = %s",
                (identity_name,),
            ).fetchone()
            return row[0] if row else 0

    def count_all(self) -> int:
        """Total number of stored embeddings."""
        with self._connect() as conn:
            row = conn.execute("SELECT COUNT(*) FROM face_embeddings").fetchone()
            return row[0] if row else 0


# Module-level singleton
_service: Optional[PgVectorService] = None


def get_pgvector_service() -> PgVectorService:
    global _service
    if _service is None:
        _service = PgVectorService()
    return _service
