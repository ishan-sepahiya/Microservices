from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "File Service"
    DEBUG: bool = False

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/2"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # MinIO (S3-compatible storage)
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str = "uploads"
    MINIO_SECURE: bool = False

    # Limits
    MAX_FILE_SIZE_MB: int = 50

    # JWT (to validate tokens from user service)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # Internal service URLs
    USER_SERVICE_URL: str = "http://user-service:8000"

    class Config:
        env_file = ".env"


settings = Settings()
