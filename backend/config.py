from pydantic_settings import BaseSettings
from pydantic import ConfigDict

class Settings(BaseSettings):
    # API Configuration
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Campus Entity Resolution"

    # Neo4j Configuration (override with environment variables)
    NEO4J_URI: str = "neo4j://neo4j:7687" # Set via GitLab secret
    NEO4J_USER: str = "neo4j" # Set via GitLab secret
    NEO4J_PASSWORD: str = ""  # Set via GitLab secret

    # PostgreSQL Configuration (override with environment variables)
    POSTGRES_SERVER: str = "db" # Set via GitLab secret
    POSTGRES_USER: str = "postgres" # Set via GitLab secret
    POSTGRES_PASSWORD: str = ""  # Set via GitLab secret
    POSTGRES_DB: str = "ethos_iitg" # Set via GitLab secret
    POSTGRES_PORT: int = 5432

    # Redis Configuration
    REDIS_HOST: str = "redis" # Set via GitLab secret
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    # Application Settings
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"
    SECRET_KEY: str = ""  # REQUIRED: Set via environment variable - see .env.example
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # JWT Configuration (for better-auth integration)
    BETTER_AUTH_SECRET: str = ""  # REQUIRED: Must match auth service BETTER_AUTH_SECRET
    AUTH_SERVICE_URL: str = ""    # REQUIRED: Public URL of the auth service VPS (e.g. https://auth.fazri.com)
    AUTH_DATABASE_URL: str = ""   # Direct connection to auth service PostgreSQL (for cross-service queries)

    # File Paths
    DATA_DIR: str = "/app/augmented"
    MODELS_DIR: str = "/app/models"
    LOGS_DIR: str = "/app/logs"

    # ML/AI Configuration
    ML_MODEL_CACHE_SIZE: int = 10
    PREDICTION_BATCH_SIZE: int = 32

    # GitLab Integration Configuration
    GITLAB_URL: str = "https://gitlab.com"
    GITLAB_TOKEN: str = ""  # Personal Access Token with read_api scope
    GITLAB_PROJECT_ID: str = ""  # e.g., "username/repo" or numeric ID

    # Chatbot Configuration (Gemini API / Vertex AI)
    GOOGLE_API_KEY: str = ""  # Set via environment variable (for Google AI Studio)
    USE_VERTEX_AI: bool = False  # Set to True to use Vertex AI instead of Google AI Studio
    VERTEX_PROJECT_ID: str = ""  # Google Cloud Project ID for Vertex AI
    VERTEX_LOCATION: str = "us-central1"  # Vertex AI location
    CHATBOT_MODEL: str = "gemini-2.5-flash"
    CHATBOT_MAX_TOKENS: int = 4096
    CHATBOT_TEMPERATURE: float = 0.3
    CHATBOT_MAX_TOOL_CALLS: int = 5
    CHATBOT_CONVERSATION_TTL: int = 3600  # 1 hour in seconds
    CHATBOT_ENABLED: bool = True

    # Sentry Configuration (Error Tracking & Performance Monitoring)
    SENTRY_DSN: str = ""  # Set via environment variable
    SENTRY_ENVIRONMENT: str = "development"  # development, staging, production
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 10% of transactions for performance monitoring
    SENTRY_ENABLED: bool = False  # Enable Sentry error tracking

    # Anomaly Detection
    ANOMALY_DETECTION_ENABLED: bool = True
    ANOMALY_CACHE_TTL_SECONDS: int = 300

    # =========================================================================
    # Alert System Configuration
    # =========================================================================

    # Alert System Feature Flags
    ALERT_SYSTEM_ENABLED: bool = True
    DEMO_MODE_ENABLED: bool = True
    ALERT_COOLDOWN_SECONDS: int = 60  # Suppress duplicate alerts for same face/stream within this window

    # Assignment Configuration
    ALERT_MAX_CONCURRENT_PER_STAFF: int = 3  # Max alerts per staff member
    ALERT_PROXIMITY_MAX_METERS: int = 100  # Initial search radius
    ALERT_PROXIMITY_GROWTH_METERS: int = 50  # Grow search by this amount
    ALERT_MAX_SEARCH_RADIUS_METERS: int = 500  # Maximum search radius

    # Assignment Weights (must sum to 1.0)
    ALERT_WEIGHT_PROXIMITY: float = 0.5
    ALERT_WEIGHT_WORKLOAD: float = 0.3
    ALERT_WEIGHT_SKILL_MATCH: float = 0.2

    # Escalation Configuration
    ALERT_ESCALATION_NO_ACK_MINUTES: int = 5  # Escalate if not acknowledged
    ALERT_ESCALATION_NO_RESOLUTION_MINUTES: int = 30  # Escalate if not resolved
    ALERT_MAX_ESCALATIONS: int = 2  # Maximum escalation count

    # Notification Configuration
    ALERT_NOTIFICATION_MAX_RETRIES: int = 3
    ALERT_NOTIFICATION_RETRY_BACKOFF: list = [10, 60, 300]  # Seconds between retries

    # Demo Configuration
    DEMO_DEFAULT_SPEED: float = 1.0
    DEMO_AUTO_ADVANCE: bool = True


    # Notification Channel Flags
    EMAIL_ENABLED: bool = True
    SMS_ENABLED: bool = True
    PUSH_ENABLED: bool = True
    NOTIFICATION_MOCK_MODE: bool = True  # If True, don't actually send notifications

    # Email Configuration (SMTP)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAIL_FROM_ADDRESS: str = "alerts@fazri.campus"

    # SMS Configuration (Twilio)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # Push Notification Configuration (Firebase)
    FIREBASE_CREDENTIALS_PATH: str = ""

    # Legacy keys (for compatibility)
    SENDGRID_API_KEY: str = ""
    FCM_SERVER_KEY: str = ""

    # Database Pool Settings
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    # =========================================================================
    # DeepFace Integration
    # =========================================================================

    DEEPFACE_ENABLED: bool = True
    # URL of the DeepFace server (container-to-container: http://deepface-server:8000)
    DEEPFACE_SERVER_URL: str = "http://deepface-server:8000"
    # HMAC-SHA256 secret for webhook signature validation; empty = skip (dev only)
    DEEPFACE_WEBHOOK_SECRET: str = ""
    # Face distance threshold: 0.0 = identical, >0.60 = no match (tuned for RTSP quality)
    DEEPFACE_CONFIDENCE_THRESHOLD: float = 0.60
    # Distance above which to flag a "low confidence" anomaly even if within threshold
    DEEPFACE_LOW_CONFIDENCE_DISTANCE: float = 0.45
    # How long in minutes before a second detection in a different zone is "impossible travel"
    DEEPFACE_IMPOSSIBLE_TRAVEL_MINUTES: int = 5
    # Interval for batch sync from DeepFace pgvector DB (seconds); 0 = disabled
    DEEPFACE_BATCH_SYNC_INTERVAL_SECONDS: int = 300
    # Connection string to the DeepFace pgvector Postgres DB (for batch sync)
    DEEPFACE_POSTGRES_URI: str = "postgresql://deepface:deepface@deepface-postgres:5432/deepface"

    # =========================================================================
    # MediaMTX RTSP Relay
    # =========================================================================

    GO2RTC_API_URL: str = "http://go2rtc:1984"       # HTTP API + WebUI + HLS + WebRTC + snapshots
    GO2RTC_RTSP_URL: str = "rtsp://go2rtc:8554"     # RTSP re-publish (DeepFace consumes here)
    GO2RTC_ENABLED: bool = True

    # =========================================================================
    # Discord Webhook
    # =========================================================================
    # Incoming webhook URL for unknown-face alert notifications.
    # Leave empty to disable.
    DISCORD_WEBHOOK_URL: str = ""

    # =========================================================================
    # Web Push (VAPID)
    # =========================================================================
    VAPID_PRIVATE_KEY: str = ""  # Base64url-encoded VAPID private key
    VAPID_PUBLIC_KEY: str = ""   # Base64url-encoded VAPID public key (sent to clients)
    VAPID_CLAIMS_EMAIL: str = "alerts@fazri.campus"  # mailto: claim in VAPID JWT

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra fields instead of raising an error
    )

settings = Settings()