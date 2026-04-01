from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1  # keep 1; InsightFace model cache is not thread-safe

    # InsightFace — detection + recognition
    det_size: int = 640             # SCRFD detection input size (640 = good balance of speed/accuracy)
    det_thresh: float = 0.6         # SCRFD detection confidence threshold (0.5=default, raise to reduce false positives)
    cosine_threshold: float = 0.55  # cosine distance — L2-normalized embeddings are more stable than DeepFace's

    # PostgreSQL / pgvector
    deepface_postgres_uri: str = (
        "postgresql://deepface:deepface@localhost:5432/deepface"
    )

    # Face tracking — assigns stable IDs to unknown faces across frames
    face_track_similarity: float = 0.65  # cosine similarity (not distance) — tighter with L2-norm embeddings
    face_track_ttl: int = 120            # seconds to remember a tracked face after last seen

    # Webhook signing — must match DEEPFACE_WEBHOOK_SECRET on the backend
    deepface_webhook_secret: str = ""

    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1
    sentry_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
