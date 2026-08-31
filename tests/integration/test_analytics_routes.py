"""Integration tests for analytics API routes and APIResponseDTO envelope."""

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from src.adapters.controllers.analytics_controller import AnalyticsController
from src.application.dtos.analytics_dtos import (
    AnalyticsDigestResponseDTO,
    CalculatedKpisDTO,
    DeepSeekUsageDTO,
    MarketingActionValidationDTO,
    TokenUsageDTO,
    UsageResponseDTO,
)
from src.infrastructure.fastapi.routes.analytics_routes import (
    get_analytics_controller,
)
from src.infrastructure.fastapi.server import create_app


@pytest.fixture
def mock_analytics_controller() -> MagicMock:
    mock_ctrl = MagicMock(spec=AnalyticsController)
    mock_ctrl.get_digest.return_value = AnalyticsDigestResponseDTO(
        status="success",
        timestamp_utc="2026-08-28 20:00:00 UTC",
        days_analyzed=1,
        pacing_severity="normal",
        kpis=CalculatedKpisDTO(
            ctr_percent=5.0,
            cpc_avg_ars=100.0,
            cpa_ars=500.0,
            conversion_rate_percent=10.0,
            pacing_percent=30.0,
            budget_limit_ars=1500.0,
            spent_today_ars=450.0,
            projected_daily_spend_ars=900.0,
        ),
        campaigns=[],
        conversions=[],
        top_pages=[],
        anomalies=[],
        search_terms=[],
        intent_recording_urls={"whatsapp_click": "https://clarity.microsoft.com/rec"},
        resumen_markdown="Resumen mock",
    )
    mock_ctrl.validate_marketing_action.return_value = MarketingActionValidationDTO(
        valid=True,
        action_type="adjust_budget",
        message="Acción validada y autorizada.",
        params={"new_budget_ars": 1200.0},
    )
    mock_ctrl.get_summary.return_value = {
        "status": "success",
        "service": "datamaq-analytics-hub",
    }
    mock_ctrl.get_ads_pacing.return_value = {
        "spent_ars": 450.0,
        "daily_budget_limit_ars": 1500.0,
    }
    mock_ctrl.get_ads_campaigns.return_value = {
        "status": "success",
        "campaigns": [],
    }
    mock_ctrl.get_ads_search_terms.return_value = {
        "status": "success",
        "terms": [],
    }
    mock_ctrl.get_ga4_conversions.return_value = {
        "status": "success",
        "rows": [],
    }
    mock_ctrl.get_clarity_insights.return_value = {
        "status": "success",
        "project_id": "wx5hfvmv5y",
    }
    mock_ctrl.get_api_usage.return_value = UsageResponseDTO(
        deepseek=DeepSeekUsageDTO(is_available=True, balance=25.5, currency="USD"),
        agy=TokenUsageDTO(input_tokens=72000, output_tokens=15000, cached_tokens=3000),
    )
    return mock_ctrl


@pytest.fixture
def client(mock_analytics_controller: MagicMock) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_analytics_controller] = lambda: (
        mock_analytics_controller
    )
    return TestClient(app)


def test_get_analytics_digest_envelope(client: TestClient) -> None:
    """Verifica que /analytics/digest retorna el envelope estándar APIResponseDTO."""
    resp = client.get("/api/v1/analytics/digest?days=1")
    assert resp.status_code == 200
    json_data = resp.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert json_data["data"]["status"] == "success"
    assert json_data["data"]["kpis"]["spent_today_ars"] == 450.0
    assert json_data["data"]["pacing_severity"] == "normal"


def test_post_analytics_actions_validate_envelope(client: TestClient) -> None:
    """Verifica que /analytics/actions/validate retorna el envelope estándar APIResponseDTO."""
    payload = {
        "action_type": "adjust_budget",
        "params": {"new_budget_ars": 1200.0},
    }
    resp = client.post("/api/v1/analytics/actions/validate", json=payload)
    assert resp.status_code == 200
    json_data = resp.json()
    assert json_data["success"] is True
    assert "data" in json_data
    assert json_data["data"]["valid"] is True
    assert json_data["data"]["action_type"] == "adjust_budget"


def test_get_analytics_summary_envelope(client: TestClient) -> None:
    """Verifica que /analytics/summary retorna el envelope estándar APIResponseDTO."""
    resp = client.get("/api/v1/analytics/summary")
    assert resp.status_code == 200
    json_data = resp.json()
    assert json_data["success"] is True
    assert json_data["data"]["service"] == "datamaq-analytics-hub"


def test_get_analytics_ads_endpoints_envelope(client: TestClient) -> None:
    """Verifica que los endpoints de Ads retornan el envelope estándar APIResponseDTO."""
    resp_pacing = client.get("/api/v1/analytics/ads/pacing")
    assert resp_pacing.status_code == 200
    assert resp_pacing.json()["success"] is True
    assert resp_pacing.json()["data"]["spent_ars"] == 450.0

    resp_camps = client.get("/api/v1/analytics/ads/campaigns?days=7")
    assert resp_camps.status_code == 200
    assert resp_camps.json()["success"] is True

    resp_terms = client.get("/api/v1/analytics/ads/search-terms?days=7&limit=10")
    assert resp_terms.status_code == 200
    assert resp_terms.json()["success"] is True


def test_get_analytics_ga4_and_clarity_envelope(client: TestClient) -> None:
    """Verifica que GA4 y Clarity retornan el envelope estándar APIResponseDTO."""
    resp_ga4 = client.get("/api/v1/analytics/ga4/conversions?days=7")
    assert resp_ga4.status_code == 200
    assert resp_ga4.json()["success"] is True

    resp_clarity = client.get("/api/v1/analytics/clarity/live")
    assert resp_clarity.status_code == 200
    assert resp_clarity.json()["success"] is True
    assert resp_clarity.json()["data"]["project_id"] == "wx5hfvmv5y"


def test_get_analytics_usage_envelope(client: TestClient) -> None:
    """Verifica que /analytics/usage retorna el envelope estándar APIResponseDTO."""
    resp = client.get("/api/v1/analytics/usage")
    assert resp.status_code == 200
    json_data = resp.json()
    assert json_data["success"] is True
    assert json_data["data"]["deepseek"]["is_available"] is True
    assert json_data["data"]["deepseek"]["balance"] == 25.5
    assert json_data["data"]["agy"]["input_tokens"] == 72000


def test_post_analytics_usage_local_envelope(
    client: TestClient, mock_analytics_controller: MagicMock
) -> None:
    """Verifica que /analytics/usage/local llama al controlador con los datos correctos."""
    payload = {
        "input_tokens": 1000,
        "output_tokens": 200,
        "cached_tokens": 5000,
    }
    resp = client.post("/api/v1/analytics/usage/local", json=payload)
    assert resp.status_code == 200
    json_data = resp.json()
    assert json_data["success"] is True
    assert json_data["data"]["status"] == "sincronizado"
    mock_analytics_controller.guardar_usage_local.assert_called_once()
