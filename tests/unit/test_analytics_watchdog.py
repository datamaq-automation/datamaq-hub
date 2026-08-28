"""Tests unitarios para scripts/analytics_watchdog.py (DataMaq Hub)."""

from unittest.mock import MagicMock

import pytest

from scripts.analytics_watchdog import (
    run_watchdog,
    send_telegram_alert,
)


def test_send_telegram_alert_missing_credentials() -> None:
    """Verifica que sin credenciales no se envíen alertas a Telegram."""
    assert not send_telegram_alert("test", "", "")
    assert not send_telegram_alert("test", "token", "")


def test_send_telegram_alert_success(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica envío exitoso a Telegram con mock HTTP."""
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    def mock_urlopen(req: object, timeout: int = 10) -> MagicMock:
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    assert send_telegram_alert("test message", "fake_bot_token", "12345")


def test_send_telegram_alert_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica manejo de errores de red al enviar a Telegram."""

    def mock_urlopen_fail(req: object, timeout: int = 10) -> object:
        raise OSError("Connection refused")

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_fail)
    assert not send_telegram_alert("test message", "fake_bot_token", "12345")


def test_run_watchdog_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifica ejecución del watchdog determinístico en modo dry-run."""
    monkeypatch.setattr(
        "src.adapters.gateways.google_ads_gateway.GoogleAdsGateway.get_daily_budget_pacing",
        lambda self: {
            "status": "success",
            "spent_ars": 100.0,
            "daily_budget_limit_ars": 1500.0,
        },
    )
    monkeypatch.setattr(
        "src.adapters.gateways.google_ads_gateway.GoogleAdsGateway.get_campaign_performance",
        lambda self, days=1: {"status": "success", "campaigns": []},
    )
    monkeypatch.setattr(
        "src.adapters.gateways.google_ads_gateway.GoogleAdsGateway.get_search_terms_report",
        lambda self, days=1, limit=20: {"status": "success", "terms": []},
    )
    monkeypatch.setattr(
        "src.adapters.gateways.ga4_gateway.GA4Gateway.get_conversions",
        lambda self, days=1: {"status": "success", "rows": []},
    )
    monkeypatch.setattr(
        "src.adapters.gateways.ga4_gateway.GA4Gateway.get_top_pages",
        lambda self, days=1, limit=5, segment="all": {"status": "success", "rows": []},
    )
    monkeypatch.setattr(
        "src.adapters.gateways.clarity_gateway.ClarityGateway.get_intent_recording_urls",
        lambda self: {
            "whatsapp_click": "https://clarity.microsoft.com/recordings?filter=wa"
        },
    )

    result = run_watchdog(dry_run=True, budget_limit_ars=1500.0)
    assert result["status"] == "success"
    assert result["telegram_sent"] is False
    assert result["kpis"]["spent_today_ars"] == 100.0
    assert "DataMaq Analytics Digest" in result["resumen_markdown"]
