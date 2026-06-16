import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "C2-App-053 AI Literature Review API"
    app_env: Literal["development", "production", "test"] = "development"
    app_port: int = Field(default=8000, ge=1, le=65535)
    app_host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # Database
    database_url: str = "postgresql+asyncpg://c2user:c2pass@localhost:5432/c2db"

    # Auth
    secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_default(cls, v: str, info) -> str:
        app_env = (info.data or {}).get("app_env", "development")
        if app_env == "production" and v == "change-me":
            raise ValueError("SECRET_KEY must be changed from the default in production")
        return v

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # AI / LLM
    gemini_api_key: str = ""
    fernet_secret_key: str = ""

    @field_validator("fernet_secret_key")
    @classmethod
    def warn_if_fernet_key_empty(cls, v: str, info) -> str:
        if not v:
            app_env = (info.data or {}).get("app_env", "development")
            if app_env == "production":
                raise ValueError("FERNET_SECRET_KEY phải được cấu hình trong môi trường production")
            logger.warning(
                "FERNET_SECRET_KEY chưa được cấu hình. Dùng ephemeral key cho dev/test."
            )
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
