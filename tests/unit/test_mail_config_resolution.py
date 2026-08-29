"""Pruebas unitarias de resolución de cuentas mail con fallback inteligente y alias.

Cubre los escenarios definidos en `specs/mail_reader.md` §4.1 y §1.4:
  1. Resolución directa de la cuenta `abc`.
  2. Resolución vía alias semánticos (`docente`, `abc.gob.ar`, `gmail`, `google`).
  3. Fallback inteligente a la única cuenta configurada cuando el default
     IMAP clásico carece de credenciales (usuario y clave vacíos).
  4. `AccountNotFoundError` enriquecido con las cuentas disponibles.
"""

import pytest

from src.domain.mail.exceptions import AccountNotFoundError
from src.infrastructure.pydantic.config import MailAccountConfig, Settings


def _settings_with_abc_oauth2() -> Settings:
    """Construye un Settings con la cuenta 'abc' vía OAuth2 y default sin credenciales."""
    return Settings(
        default_mail_account="openclaw@datamaq.com.ar",
        mail_imap_user="",
        mail_imap_pass="",
        google_ads_client_id="CLIENT_ID_GLOBAL",
        google_ads_client_secret="CLIENT_SECRET_GLOBAL",
        mail_accounts={
            "abc": MailAccountConfig(
                host="imap.gmail.com",
                port=993,
                user="agustinbustos@abc.gob.ar",
                password="",
                oauth2_client_id="",
                oauth2_client_secret="",
                oauth2_refresh_token="REFRESH_ABC",
                use_ssl=True,
                timeout_seconds=15,
            )
        },
    )


def test_resolve_account_explicit_abc():
    """Escenario 1: la consulta explícita ?account=abc resuelve la cuenta ABC."""
    settings = _settings_with_abc_oauth2()

    cfg = settings.get_mail_account_config("abc")

    assert cfg.host == "imap.gmail.com"
    assert cfg.user == "agustinbustos@abc.gob.ar"
    assert cfg.oauth2_refresh_token == "REFRESH_ABC"
    assert cfg.timeout_seconds == 15


def test_resolve_account_aliases():
    """Escenario 2: los alias semánticos y el correo completo resuelven a 'abc'."""
    settings = _settings_with_abc_oauth2()

    for alias in (
        "docente",
        "abc.gob.ar",
        "gmail",
        "google",
        "agustinbustos@abc.gob.ar",
    ):
        cfg = settings.get_mail_account_config(alias)
        assert cfg.user == "agustinbustos@abc.gob.ar", (
            f"alias {alias!r} no resolvió a abc"
        )


def test_intelligent_fallback_when_default_unconfigured():
    """Escenario 3: si el default IMAP carece de credenciales y hay una única cuenta,
    se selecciona automáticamente la primera cuenta configurada ('abc')."""
    settings = _settings_with_abc_oauth2()

    cfg = settings.get_mail_account_config(None)

    assert settings.mail_imap_user == ""
    assert cfg.user == "agustinbustos@abc.gob.ar"
    assert cfg.oauth2_refresh_token == "REFRESH_ABC"


def test_intelligent_fallback_respects_configured_imap_default():
    """Regresión: si el default IMAP clásico SÍ tiene credenciales, no se aplica el fallback."""
    settings = Settings(
        default_mail_account="datamaq",
        mail_imap_user="info@datamaq.com.ar",
        mail_imap_pass="corp_pass",
        mail_accounts={
            "abc": MailAccountConfig(
                host="imap.gmail.com",
                port=993,
                user="docente@abc.gob.ar",
                password="abc_app_password",
            )
        },
    )

    cfg = settings.get_mail_account_config(None)

    assert cfg.user == "info@datamaq.com.ar"


def test_default_mail_account_alias_abc_direct():
    """Escenario: si DEFAULT_MAIL_ACCOUNT=abc, se resuelve directamente sin fallback."""
    settings = Settings(
        default_mail_account="abc",
        mail_imap_user="",
        mail_imap_pass="",
        mail_accounts={
            "abc": MailAccountConfig(
                host="imap.gmail.com",
                port=993,
                user="agustinbustos@abc.gob.ar",
                oauth2_refresh_token="REFRESH_ABC",
                use_ssl=True,
                timeout_seconds=15,
            )
        },
    )

    cfg = settings.get_mail_account_config()

    assert cfg.user == "agustinbustos@abc.gob.ar"


def test_oauth2_injection_from_global_credentials():
    """Escenario: si la cuenta ABC tiene refresh_token pero no client_id/secret,
    hereda los valores globales GOOGLE_ADS_CLIENT_ID/SECRET."""
    settings = _settings_with_abc_oauth2()

    cfg = settings.get_mail_account_config("abc")

    assert cfg.oauth2_client_id == "CLIENT_ID_GLOBAL"
    assert cfg.oauth2_client_secret == "CLIENT_SECRET_GLOBAL"


def test_account_not_found_lists_available():
    """Escenario 4: una cuenta inexistente lanza AccountNotFoundError con
    details['cuentas_disponibles'] poblado."""
    settings = _settings_with_abc_oauth2()

    with pytest.raises(AccountNotFoundError) as exc_info:
        settings.get_mail_account_config("cuenta_inexistente")

    exc = exc_info.value
    assert exc.account == "cuenta_inexistente"
    assert "cuenta_inexistente" in str(exc)
    assert exc.details is not None
    assert exc.details["cuentas_disponibles"] == ["abc"]
