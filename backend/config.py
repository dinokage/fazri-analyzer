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
    SECRET_KEY: str = "REMOVED_FROM_HISTORY_USE_ENV_VARS"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # File Paths
    DATA_DIR: str = "/app/augmented"
    MODELS_DIR: str = "/app/models"
    LOGS_DIR: str = "/app/logs"

    # ML/AI Configuration
    ML_MODEL_CACHE_SIZE: int = 10
    PREDICTION_BATCH_SIZE: int = 32

    # Chatbot Configuration (Gemini API / Vertex AI)
    GOOGLE_API_KEY: str = ""  # Set via environment variable (for Google AI Studio)
    USE_VERTEX_AI: bool = False  # Set to True to use Vertex AI instead of Google AI Studio
    VERTEX_PROJECT_ID: str = ""  # Google Cloud Project ID for Vertex AI
    VERTEX_LOCATION: str = "us-central1"  # Vertex AI location
    CHATBOT_MODEL: str = "gemini-2.0-flash"
    CHATBOT_MAX_TOKENS: int = 4096
    CHATBOT_TEMPERATURE: float = 0.3
    CHATBOT_MAX_TOOL_CALLS: int = 5
    CHATBOT_CONVERSATION_TTL: int = 3600  # 1 hour in seconds
    CHATBOT_ENABLED: bool = True

    # Anomaly Detection
    ANOMALY_DETECTION_ENABLED: bool = True
    ANOMALY_CACHE_TTL_SECONDS: int = 300

    # Database Pool Settings
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    DATABASE_POOL_RECYCLE: int = 3600

    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'  # Ignore extra fields instead of raising an error
    )

settings = Settings()