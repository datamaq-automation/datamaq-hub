"""Tests unitarios para el servidor FastMCP de Google Ads (DataMaq)."""

import pytest

import src.infrastructure.fastmcp.google_ads as google_ads_mcp
from src.adapters.gateways.google_ads_gateway import (
    DAILY_BUDGET_LIMIT_ARS,
    GoogleAdsGateway,
)


def test_google_ads_status_structure() -> None:
    status = google_ads_mcp.get_google_ads_status()
    assert "status" in status
    assert "daily_budget_limit_ars" in status
    assert status["daily_budget_limit_ars"] == DAILY_BUDGET_LIMIT_ARS


def test_google_ads_missing_credentials_handling(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_gateway = GoogleAdsGateway(
        developer_token="",
        client_id="",
        client_secret="",
        refresh_token="",
        customer_id="",
    )
    monkeypatch.setattr(google_ads_mcp, "_gateway", mock_gateway)

    status = google_ads_mcp.get_google_ads_status()
    assert status["status"] == "pending_credentials"

    camp = google_ads_mcp.get_campaign_performance(7)
    assert camp["status"] == "missing_credentials"

    terms = google_ads_mcp.get_search_terms_report(7)
    assert terms["status"] == "missing_credentials"

    pacing = google_ads_mcp.get_daily_budget_pacing()
    assert pacing["status"] == "missing_credentials"
    assert pacing["daily_limit_ars"] == 1500.0
