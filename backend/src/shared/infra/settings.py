import logging
from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator, model_validator
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

    # Async worker / ingestion (Story 2.5)
    # arq_redis_url: để rỗng thì tự lấy theo redis_url (xem validator bên dưới). Chỉ cần
    # set ARQ_REDIS_URL khi muốn arq dùng Redis KHÁC với redis_url — tránh tình trạng chỉ
    # cấu hình REDIS_URL (vd trong docker) nhưng worker lại trỏ về localhost mặc định.
    arq_redis_url: str = Field(default="")
    worker_concurrency: int = 2  # NFR4: concurrency_limit=2
    ingestion_sse_ticket_ttl: int = 60  # TTL ticket SSE (giây)
    ingestion_progress_ttl: int = 3600  # TTL key progress trong Redis (giây)

    @model_validator(mode="after")
    def _default_arq_redis_url(self) -> "Settings":
        if not self.arq_redis_url:
            self.arq_redis_url = self.redis_url
        return self

    # Search
    broad_query_threshold: int = 50

    # File Upload
    upload_dir: str = "data/uploads"
    max_upload_size_mb: int = 20
    papers_dir: str = "data/papers"

    # Neo4j (Story 4.1)
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = "neo4jpassword"

    # Graph sync settings (Story 4.1)
    # MAX_SYNC_RETRIES + GC_RETENTION_DAYS → admin settings (system_settings), KHÔNG để env
    # (chính sách/độ tin cậy do Admin cấu hình runtime). SYNC_OUTBOX_BATCH_SIZE giữ ở env vì là
    # knob hạ tầng gắn RAM (ARCH-1) — không nên cho admin chỉnh để tránh OOM worker.
    sync_outbox_batch_size: int = 100

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
