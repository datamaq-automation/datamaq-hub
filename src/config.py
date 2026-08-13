"""Application configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Datamaq Hub - Receipt Parser API"
    app_version: str = "0.1.0"
    app_description: str = "API REST especializada en extracción y parsing de recibos de sueldo (DGCyE PBA y estándar)."
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]
    max_upload_size_bytes: int = 25 * 1024 * 1024  # 25 MB


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()
