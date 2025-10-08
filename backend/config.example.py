from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Campus Entity Resolution"
    NEO4J_URI: str = "<neo4j-url>"
    NEO4J_USER: str = "<neo4j-user>"
    NEO4J_PASSWORD: str = "<neo4j-password>"
    POSTGRES_SERVER: str = "<postgres-server>"
    POSTGRES_USER: str = "<postgres-user>"
    POSTGRES_PASSWORD: str = "<postgres-password>"
    POSTGRES_DB: str = "ethos_iitg"
    REDIS_HOST: str = "<redis-host>"
    REDIS_PORT: int = 6379
    
    class Config:
        env_file = ".env"

settings = Settings()