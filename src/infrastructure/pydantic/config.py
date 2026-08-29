"""Infrastructure configuration using pydantic-settings."""

from functools import lru_cache

from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MailAccountConfig(BaseModel):
    """Configuración de conexión para una cuenta de correo IMAP (soporta básico y OAuth2)."""

    host: str = "127.0.0.1"
    port: int = 993
    user: str = ""
    password: str = ""
    use_ssl: bool = True
    timeout_seconds: int = 10
    oauth2_client_id: str = ""
    oauth2_client_secret: str = ""
    oauth2_refresh_token: str = ""


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

    # === BASE DE DATOS MySQL (Caché de APIs externas — schema datamaq_hub) ===
    # Formato: mysql+pymysql://usuario:password@host/datamaq_hub
    # En VPS: mysql+pymysql://datamaq:PASSWORD@127.0.0.1:3306/datamaq_hub
    database_url: str = ""

    # === TELEGRAM BOT & ALERTAS (Watchdog) ===
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # === SERVIDOR DE CORREO IMAP (Lectura para OpenClaw — Configuración Base) ===
    mail_imap_host: str = "127.0.0.1"
    mail_imap_port: int = 993
    mail_imap_user: str = ""
    mail_imap_pass: str = ""
    mail_imap_use_ssl: bool = True
    mail_imap_timeout_seconds: int = 10

    # === CUENTAS DE CORREO MULTI-CUENTA (DataMaq, ABC Docente, etc.) ===
    default_mail_account: str = "openclaw@datamaq.com.ar"
    mail_accounts: dict[str, MailAccountConfig] = Field(
        default_factory=dict[str, MailAccountConfig]
    )

    # === BASE DE DATOS ROUNDCUBE (Contactos y Calendario) ===
    roundcube_db_url: str = "sqlite:///data/roundcube.db"

    # === TTLs de caché por prefijo de clave (segundos) ===
    # JSON en .env. Vacío = el gateway usa sus defaults aprobados (fallback).
    # Ejemplo: CACHE_TTLS={"google_ads:daily_budget_pacing": 900}
    cache_ttls: dict[str, int] = Field(default_factory=dict[str, int])

    def get_mail_account_config(
        self, account_name: str | None = None
    ) -> MailAccountConfig:
        """Obtiene la configuración de la cuenta solicitada con fallback seguro e inteligente."""
        raw_target = (account_name or self.default_mail_account).strip().lower()

        # Mapeo de alias semánticos comunes hacia la cuenta docente ABC
        alias_map = {
            "docente": "abc",
            "abc.gob.ar": "abc",
            "gmail": "abc",
            "google": "abc",
        }
        target = alias_map.get(raw_target, raw_target)

        config_obj: MailAccountConfig | None = None
        if target in self.mail_accounts:
            config_obj = self.mail_accounts[target].model_copy()
        else:
            for name, config in self.mail_accounts.items():
                if name.lower() == target or config.user.lower() == target:
                    config_obj = config.model_copy()
                    break

        if config_obj is not None:
            return self._with_oauth2_fallback(config_obj)

        # Fallback a las variables top-level clásicas o a la única cuenta en MAIL_ACCOUNTS
        if target in (
            self.default_mail_account.lower(),
            "datamaq",
            "default",
            "openclaw@datamaq.com.ar",
        ):
            # Si el default IMAP no tiene usuario ni clave configurados, pero hay cuentas en
            # MAIL_ACCOUNTS, usar la primera/única cuenta (fallback inteligente para OpenClaw).
            if (
                not self.mail_imap_user
                and not self.mail_imap_pass
                and self.mail_accounts
            ):
                first_name = next(iter(self.mail_accounts))
                return self._with_oauth2_fallback(
                    self.mail_accounts[first_name].model_copy()
                )

            return MailAccountConfig(
                host=self.mail_imap_host,
                port=self.mail_imap_port,
                user=self.mail_imap_user,
                password=self.mail_imap_pass,
                use_ssl=self.mail_imap_use_ssl,
                timeout_seconds=self.mail_imap_timeout_seconds,
            )

        from src.domain.mail.exceptions import AccountNotFoundError

        disponibles = list(self.mail_accounts.keys())
        raise AccountNotFoundError(
            account=account_name or self.default_mail_account,
            available_accounts=disponibles,
        )

    def _with_oauth2_fallback(self, config: MailAccountConfig) -> MailAccountConfig:
        """Inyecta los client_id/secret globales en una cuenta OAuth2 si faltan."""
        if config.oauth2_refresh_token:
            if not config.oauth2_client_id:
                config.oauth2_client_id = self.google_ads_client_id
            if not config.oauth2_client_secret:
                config.oauth2_client_secret = self.google_ads_client_secret
        return config


@lru_cache
def get_settings() -> Settings:
    """Cached settings provider."""
    return Settings()
