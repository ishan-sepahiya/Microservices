from functools import lru_cache
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(Path(__file__).parent.parent.parent / ".env"),
        case_sensitive=False
    )

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    debug: bool = False

    agent_api_key: str = "change-me-agent-internal-key"

    # Downstream service URLs (used by monitoring + debug agent)
    product_service_url: str = "http://product-service:8001"
    payment_service_url: str = "http://payment-service:8002"
    chat_service_url: str    = "http://chat-service:8011"
    metrics_service_url: str = "http://metrics-service:8012"

    # Ollama LLM
    ollama_url: str   = "http://ollama:11434/api/generate"
    ollama_model: str = "mistral"

    # n8n webhooks (optional)
    n8n_scale_webhook: str    = ""
    n8n_restart_webhook: str  = ""
    n8n_rollback_webhook: str = ""
    n8n_debug_webhook: str    = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
