from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file="../../.env", case_sensitive=False)
    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    debug: bool = False
    agent_service_url: str = "http://agent:8020"
    agent_api_key: str = "change-me-agent-internal-key"

    # Downstream service URLs for live probing
    product_service_url: str = "http://product-service:8001"
    payment_service_url: str = "http://payment-service:8002"
    chat_service_url: str    = "http://chat-service:8011"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
