import os

# CRITICAL: must be set before any TensorFlow / DeepFace import
os.environ.setdefault("TF_USE_LEGACY_KERAS", "1")

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    workers: int = 1  # keep 1; DeepFace model cache is not thread-safe

    # DeepFace ML config
    model_name: str = "Buffalo_L"
    detector_backend: str = "yolov8n"  # better multi-face + side-profile detection than mtcnn
    distance_metric: str = "cosine"
    cosine_threshold: float = 0.60   # slightly lenient for RTSP camera quality; tune via env var
    enforce_detection: bool = True
    expand_percentage: int = 10      # include ~10% padding around detected faces for better embeddings
    l2_normalize: bool = False
    normalization: str = "raw"        # Buffalo_L needs [0,255] input; "raw" restores from [0,1]
    jpeg_quality: int = 95           # higher quality for better face detail on distant faces

    # PostgreSQL / pgvector
    deepface_postgres_uri: str = (
        "postgresql://deepface:deepface@localhost:5432/deepface"
    )

    # Face tracking — used to assign stable IDs to unknown faces across frames
    face_track_similarity: float = 0.60  # cosine similarity threshold for "same face"
    face_track_ttl: int = 120            # seconds to remember a tracked face after last seen

    # Webhook signing — must match DEEPFACE_WEBHOOK_SECRET on the backend
    deepface_webhook_secret: str = ""

    # Sentry
    sentry_dsn: str = ""
    sentry_environment: str = "development"
    sentry_traces_sample_rate: float = 0.1
    sentry_enabled: bool = False

    @property
    def connection_details(self) -> str:
        return self.deepface_postgres_uri

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # don't reject DEEPFACE_* env vars not declared as fields
    )


settings = Settings()

# Propagate DB settings so DeepFace's internal client picks them up
os.environ.setdefault("DEEPFACE_POSTGRES_URI", settings.deepface_postgres_uri)
os.environ.setdefault("DEEPFACE_DATABASE_TYPE", "postgres")
