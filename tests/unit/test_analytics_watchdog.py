"""Tests unitarios para scripts/analytics_watchdog.py (DataMaq Hub)."""

from typing import Any
from unittest.mock import MagicMock

import pytest

from scripts.analytics_watchdog import (
    _build_markdown_report,
    run_watchdog,
    send_telegram_alert,
)


def test_build_markdown_report_ads_within_budget() -> None:
    ads_data: dict[str, Any] = {
        "status": "ready",
        "daily_budget_pacing": {"spent_today_ars": 450.0},
        "campaign_status": "PAUSED",
    }
    ga4_data: dict[str, Any] = {
        "status": "configured",
        "conversions": {
            "rows": [
                {"eventName": "whatsapp_click", "eventCount": "3"},
                {"eventName": "direct_contact", "eventCount": "1"},
            ]
        },
        "top_pages": {
            "rows": [
                {"pagePath": "/", "screenPageViews": "42"},
            ]
        },
    }
    clarity_data: dict[str, Any] = {
        "project_info": {
            "intent_recording_urls": {
                "email_click": "https://clarity.microsoft.com/recordings?filter=email",
                "whatsapp_click": "https://clarity.microsoft.com/recordings?filter=wa",
            }
        },
        "live_insights": {"status": "success"},
    }

    report = _build_markdown_report(ads_data, ga4_data, clarity_data, 1500.0)
    assert "$450.00 ARS" in report
    assert "whatsapp_click" in report
    assert "Email Clicks" in report
    assert "✅" in report


def test_build_markdown_report_ads_over_budget() -> None:
    ads_data: dict[str, Any] = {
        "status": "ready",
        "daily_budget_pacing": {"spent_today_ars": 1650.0},
        "campaign_status": "ENABLED",
    }
    ga4_data: dict[str, Any] = {"status": "missing_credentials"}
    clarity_data: dict[str, Any] = {"live_insights": {"status": "missing_token"}}

    report = _build_markdown_report(ads_data, ga4_data, clarity_data, 1500.0)
    assert "$1,650.00 ARS" in report
    assert "⚠️" in report
    assert "missing_credentials" in report


def test_send_telegram_alert_missing_credentials() -> None:
    assert not send_telegram_alert("test", "", "")
    assert not send_telegram_alert("test", "token", "")


def test_send_telegram_alert_success(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    def mock_urlopen(req: object, timeout: int = 10) -> MagicMock:
        return mock_resp

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen)
    assert send_telegram_alert("test message", "fake_bot_token", "12345")


def test_send_telegram_alert_network_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    def mock_urlopen_fail(req: object, timeout: int = 10) -> object:
        raise OSError("Connection refused")

    monkeypatch.setattr("urllib.request.urlopen", mock_urlopen_fail)
    assert not send_telegram_alert("test message", "fake_bot_token", "12345")


def test_run_watchdog_dry_run(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.google_ads.get_google_ads_status",
        lambda: {"status": "ready"},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.google_ads.get_daily_budget_pacing",
        lambda: {"spent_today_ars": 0.0},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.google_ads.get_campaign_performance",
        lambda days: {"campaigns": []},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.ga4.get_ga4_status",
        lambda: {"status": "configured"},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.ga4.get_ga4_conversions",
        lambda days: {"rows": []},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.ga4.get_ga4_top_pages",
        lambda days: {"rows": []},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.ga4.get_ga4_traffic_sources",
        lambda days: {"rows": []},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.clarity.get_clarity_project_info",
        lambda: {"intent_recording_urls": {}},
    )
    monkeypatch.setattr(
        "src.infrastructure.fastmcp.clarity.get_live_insights",
        lambda: {"status": "success"},
    )

    result = run_watchdog(dry_run=True, budget_limit_ars=1500.0)
    assert "timestamp" in result
    assert result["telegram_sent"] is False
    assert "DataMaq Hub" in result["report_markdown"]
