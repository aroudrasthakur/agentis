from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://agentis:agentis@127.0.0.1:55432/agentis"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    vendor_mcp_url: str = "http://localhost:8100/mcp"
    frontend_origin: str = "http://localhost:3000"
    backend_origin: str = "http://localhost:8000"
    jwt_secret: str = "agentis-dev-change-me"
    agent_token_ttl_seconds: int = 3600
    session_invite_ttl_seconds: int = 86400


@lru_cache
def get_settings() -> Settings:
    return Settings()
