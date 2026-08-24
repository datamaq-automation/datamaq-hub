"""Infrastructure configuration using pydantic-settings."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application global settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Datamaq Hub - Receipt Parser API"
    app_version: str = "0.1.0"
    app_description: str = "API REST especializada en extracción y parsing de recibos de sueldo en PDF (Clean Architecture & DDD)."
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["*"]
    max_upload_size_bytes: int = 25 * 1024 * 1024  # 25 MB

    # === MICROSOFT CLARITY ===
    clarity_id: str = ""
    clarity_api_token: str = ""

    # === GOOGLE ANALYTICS 4 ===
    ga4_property_id: str = ""
    google_application_credentials: str = ""

    # === GOOGLE ADS ===
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""
    google_ads_login_customer_id: str = ""


@lru_cache
def get_settings() -> Settings:
    """Cached settings provider."""
    return Settings()
