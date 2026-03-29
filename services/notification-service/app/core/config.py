from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "Notification Service"
    DEBUG: bool = False

    DATABASE_URL: str
    REDIS_URL: str = "redis://localhost:6379/1"
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # SMTP (email)
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str
    SMTP_PASSWORD: str
    EMAIL_FROM_NAME: str = "SaaS Platform"

    # Twilio (SMS)
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_PHONE_NUMBER: str = ""

    class Config:
        env_file = ".env"


settings = Settings()
