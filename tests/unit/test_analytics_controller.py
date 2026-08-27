"""Tests unitarios para AnalyticsController y endpoints de analítica comercial."""

from unittest.mock import MagicMock

from src.adapters.controllers.analytics_controller import AnalyticsController


def test_analytics_controller_summary() -> None:
    """Verifica que get_summary consolida métricas de Google Ads, GA4 y Clarity."""
    mock_ads = MagicMock()
    mock_ads.get_daily_budget_pacing.return_value = {
        "status": "success",
        "spent_ars": 0.0,
        "daily_budget_limit_ars": 1500.0,
    }
    mock_ads.get_campaign_performance.return_value = {
        "status": "success",
        "campaigns": [{"name": "Telemetria", "status": "ENABLED"}],
    }

    mock_ga4 = MagicMock()
    mock_ga4.get_conversions.return_value = {
        "status": "success",
        "rows": [{"eventName": "whatsapp_click", "eventCount": "3"}],
    }
    mock_ga4.get_top_pages.return_value = {
        "status": "success",
        "rows": [{"pagePath": "/retrofit-iot", "screenPageViews": "10"}],
    }

    mock_clarity = MagicMock()
    mock_clarity.clarity_id = "wx5hfvmv5y"
    mock_clarity.get_intent_recording_urls.return_value = {
        "whatsapp_click": "https://clarity.microsoft.com/recordings?filter=wa",
    }

    controller = AnalyticsController(
        google_ads_gateway=mock_ads,
        ga4_gateway=mock_ga4,
        clarity_gateway=mock_clarity,
    )

    summary = controller.get_summary()
    assert summary["status"] == "success"
    assert summary["service"] == "datamaq-analytics-hub"
    assert summary["google_ads"]["pacing"]["spent_ars"] == 0.0
    assert len(summary["google_ads"]["campaigns"]) == 1
    assert len(summary["google_analytics_4"]["conversions"]) == 1
    assert len(summary["google_analytics_4"]["top_pages"]) == 1
    assert "whatsapp_click" in summary["microsoft_clarity"]["recordings"]


def test_analytics_controller_delegated_methods() -> None:
    """Verifica los métodos individuales delegados."""
    mock_ads = MagicMock()
    mock_ads.get_daily_budget_pacing.return_value = {"spent_ars": 120.0}
    mock_ads.get_campaign_performance.return_value = {"campaigns": []}
    mock_ads.get_search_terms_report.return_value = {"terms": []}

    mock_ga4 = MagicMock()
    mock_ga4.get_conversions.return_value = {"rows": []}

    mock_clarity = MagicMock()
    mock_clarity.clarity_id = "wx5hfvmv5y"
    mock_clarity.get_intent_recording_urls.return_value = {}

    controller = AnalyticsController(
        google_ads_gateway=mock_ads,
        ga4_gateway=mock_ga4,
        clarity_gateway=mock_clarity,
    )

    assert controller.get_ads_pacing()["spent_ars"] == 120.0
    assert controller.get_ads_campaigns(days=30) == {"campaigns": []}
    assert controller.get_ads_search_terms(days=14, limit=5) == {"terms": []}
    assert controller.get_ga4_conversions(days=7) == {"rows": []}
    insights = controller.get_clarity_insights()
    assert insights["project_id"] == "wx5hfvmv5y"
