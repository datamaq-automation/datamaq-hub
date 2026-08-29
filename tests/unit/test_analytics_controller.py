"""Tests unitarios para AnalyticsController y endpoints de analítica comercial."""

from unittest.mock import MagicMock

from src.adapters.controllers.analytics_controller import AnalyticsController
from src.application.dtos.analytics_dtos import MarketingActionRequestDTO


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


def test_analytics_controller_digest() -> None:
    """Verifica generación de digest consolidado desde el controlador."""
    mock_ads = MagicMock()
    mock_ads.get_daily_budget_pacing.return_value = {
        "status": "success",
        "spent_ars": 100.0,
        "daily_budget_limit_ars": 1500.0,
    }
    mock_ads.get_campaign_performance.return_value = {"campaigns": []}
    mock_ads.get_search_terms_report.return_value = {"terms": []}

    mock_ga4 = MagicMock()
    mock_ga4.get_conversions.return_value = {"rows": []}
    mock_ga4.get_top_pages.return_value = {"rows": []}

    mock_clarity = MagicMock()
    mock_clarity.clarity_id = "wx5hfvmv5y"
    mock_clarity.get_intent_recording_urls.return_value = {}

    controller = AnalyticsController(
        google_ads_gateway=mock_ads,
        ga4_gateway=mock_ga4,
        clarity_gateway=mock_clarity,
    )

    digest = controller.get_digest(days=1)
    assert digest.status == "success"
    assert digest.kpis.spent_today_ars == 100.0
    assert digest.pacing_severity == "normal"


def test_analytics_controller_action_validation() -> None:
    """Verifica validación de acciones desde el controlador."""
    mock_ads = MagicMock()
    mock_ga4 = MagicMock()
    mock_clarity = MagicMock()
    mock_clarity.clarity_id = "wx5hfvmv5y"

    controller = AnalyticsController(
        google_ads_gateway=mock_ads,
        ga4_gateway=mock_ga4,
        clarity_gateway=mock_clarity,
    )

    req = MarketingActionRequestDTO(
        action_type="add_negative_keyword",
        params={"keyword": "curso arduino"},
    )
    val = controller.validate_marketing_action(req)
    assert val.valid is True


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


def _reporte_campanas_success() -> dict:
    """Reporte Google Ads success con 2 campañas y métricas conocidas."""
    return {
        "status": "success",
        "customer_id": "4057778237",
        "period_days": 7,
        "total_campaigns": 2,
        "total_cost_ars": 300.0,
        "campaigns": [
            {
                "id": "1",
                "name": "C1",
                "status": "ENABLED",
                "impressions": 1000,
                "clicks": 100,
                "cost_ars": 200.0,
                "avg_cpc_ars": 2.0,
                "conversions": 5,
            },
            {
                "id": "2",
                "name": "C2",
                "status": "ENABLED",
                "impressions": 500,
                "clicks": 50,
                "cost_ars": 100.0,
                "avg_cpc_ars": 2.0,
                "conversions": 3,
            },
        ],
    }


def _controller_con_ads(mock_ads: MagicMock) -> AnalyticsController:
    return AnalyticsController(
        google_ads_gateway=mock_ads,
        ga4_gateway=MagicMock(),
        clarity_gateway=MagicMock(),
    )


def test_ads_campaigns_summary_agrega() -> None:
    """R-A1: summary=True consolida métricas y elimina la lista campaigns."""
    mock_ads = MagicMock()
    mock_ads.get_campaign_performance.return_value = _reporte_campanas_success()
    controller = _controller_con_ads(mock_ads)

    result = controller.get_ads_campaigns(days=7, summary=True)

    assert "campaigns" not in result
    assert result["total_campaigns"] == 2
    summary = result["summary"]
    assert summary["impressions"] == 1500
    assert summary["clicks"] == 150
    assert summary["cost_ars"] == 300.0
    assert summary["ctr_percent"] == 10.0
    assert summary["conversions"] == 8
    assert summary["cpc_avg_ars"] == 2.0


def test_ads_campaigns_full_passthrough() -> None:
    """R-A2: summary=False retorna el payload original con campaigns."""
    report = _reporte_campanas_success()
    mock_ads = MagicMock()
    mock_ads.get_campaign_performance.return_value = report
    controller = _controller_con_ads(mock_ads)

    result = controller.get_ads_campaigns(days=7, summary=False)

    assert result == report
    assert "campaigns" in result


def test_ads_campaigns_error_passthrough() -> None:
    """R-A3: status != success → passthrough sin agregación."""
    error_report = {"status": "missing_credentials", "details": {"x": 1}}
    mock_ads = MagicMock()
    mock_ads.get_campaign_performance.return_value = error_report
    controller = _controller_con_ads(mock_ads)

    result = controller.get_ads_campaigns(days=7, summary=True)

    assert result == error_report


def test_ads_campaigns_summary_ceros_defensivos() -> None:
    """R-A4: campañas vacías → summary con ceros (sin ZeroDivisionError)."""
    empty_report = {
        "status": "success",
        "customer_id": "4057778237",
        "period_days": 7,
        "total_campaigns": 0,
        "total_cost_ars": 0.0,
        "campaigns": [],
    }
    mock_ads = MagicMock()
    mock_ads.get_campaign_performance.return_value = empty_report
    controller = _controller_con_ads(mock_ads)

    result = controller.get_ads_campaigns(days=7, summary=True)

    summary = result["summary"]
    assert summary["impressions"] == 0
    assert summary["clicks"] == 0
    assert summary["cost_ars"] == 0.0
    assert summary["ctr_percent"] == 0.0
    assert summary["conversions"] == 0
    assert summary["cpc_avg_ars"] == 0.0
