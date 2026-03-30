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
    detector_backend: str = "mtcnn"
    distance_metric: str = "cosine"
    cosine_threshold: float = 0.40   # tightened from 0.55 default; reduce for fewer false positives
    enforce_detection: bool = True
    l2_normalize: bool = False
    normalization: str = "raw"        # Buffalo_L needs [0,255] input; "raw" restores from [0,1]

    # PostgreSQL / pgvector
    deepface_postgres_uri: str = (
        "postgresql://deepface:deepface@localhost:5432/deepface"
    )

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
