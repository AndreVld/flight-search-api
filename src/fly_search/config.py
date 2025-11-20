"""Application configuration using Pydantic Settings."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="FLY_SEARCH_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server settings
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port", gt=0, le=65535)
    reload: bool = Field(default=True, description="Enable auto-reload in development")

    # AviaApiAdapter settings
    max_concurrent_threads: int = Field(
        default=10,
        description="Maximum number of concurrent generator threads",
        gt=0,
        le=100,
    )
    chunk_queue_timeout: float = Field(
        default=0.1,
        description="Timeout for chunk queue get operation (seconds)",
        gt=0,
        le=10,
    )
    thread_join_timeout: float = Field(
        default=1.0,
        description="Timeout for thread join operation (seconds)",
        gt=0,
        le=60,
    )

    # Logging settings
    log_level: str = Field(
        default="INFO",
        description="Logging level",
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$",
    )

    # Cache settings
    cache_response_ttl: int = Field(
        default=180,
        description="Response cache TTL in seconds (3 minutes)",
        gt=0,
        le=3600,
    )
    cache_response_size: int = Field(
        default=100,
        description="Maximum number of cached responses",
        gt=0,
        le=10000,
    )
    cache_task_ttl: int = Field(
        default=3600,
        description="Task cache TTL in seconds (1 hour)",
        gt=0,
        le=86400,
    )
    cache_task_size: int = Field(
        default=1000,
        description="Maximum number of cached tasks",
        gt=0,
        le=100000,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Get application settings (singleton).

    Returns:
        Settings instance
    """
    return Settings()

