from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../../.env", case_sensitive=False
    )

    database_url: str
    secret_key: str
    algorithm: str = "HS256"
    debug: bool = False

    # Internal API key — services must send this to register
    agent_api_key: str = "change-me-agent-internal-key"

    # AI provider (teammates fill this in)
    ai_provider: str = "openai"          # openai | anthropic | ollama
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    ollama_base_url: str = "http://ollama:11434"


@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
