"""Tests unitarios para el servidor FastMCP de Google Ads (DataMaq)."""

import pytest

from src.infrastructure.fastmcp.google_ads import (
    DAILY_BUDGET_LIMIT_ARS,
    get_campaign_performance,
    get_daily_budget_pacing,
    get_google_ads_status,
    get_search_terms_report,
)


def test_google_ads_status_structure() -> None:
    status = get_google_ads_status()
    assert "status" in status
    assert "daily_budget_limit_ars" in status
    assert status["daily_budget_limit_ars"] == DAILY_BUDGET_LIMIT_ARS


def test_google_ads_missing_credentials_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("src.infrastructure.fastmcp.google_ads.REFRESH_TOKEN", "")
    monkeypatch.setattr("src.infrastructure.fastmcp.google_ads.CUSTOMER_ID", "")

    status = get_google_ads_status()
    assert status["status"] == "pending_credentials"

    camp = get_campaign_performance(7)
    assert camp["status"] == "missing_credentials"

    terms = get_search_terms_report(7)
    assert terms["status"] == "missing_credentials"

    pacing = get_daily_budget_pacing()
    assert pacing["status"] == "missing_credentials"
    assert pacing["daily_limit_ars"] == 1500.0
