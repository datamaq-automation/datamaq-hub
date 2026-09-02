"""Tests unitarios para el caso de uso GenerarAnalyticsDigestUseCase."""

from unittest.mock import MagicMock

from src.application.use_cases.generar_analytics_digest import (
    GenerarAnalyticsDigestUseCase,
)


def test_generar_analytics_digest_execution() -> None:
    """Verifica que el caso de uso sintetiza correctamente los datos y genera el digest."""
    mock_ads = MagicMock()
    mock_ads.get_daily_budget_pacing.return_value = {
        "status": "success",
        "spent_ars": 450.0,
        "daily_budget_limit_ars": 1500.0,
    }
    mock_ads.get_campaign_performance.return_value = {
        "status": "success",
        "campaigns": [
            {
                "id": "123",
                "name": "Telemetria IoT",
                "status": "ENABLED",
                "impressions": 500,
                "clicks": 20,
                "cost_ars": 450.0,
                "conversions": 2.0,
                "cpc_avg_ars": 22.5,
            }
        ],
    }
    mock_ads.get_search_terms_report.return_value = {
        "status": "success",
        "terms": [
            {
                "term": "telemetria de inyectoras",
                "impressions": 50,
                "clicks": 5,
                "cost_ars": 100.0,
                "conversions": 1,
            },
            {
                "term": "curso gratis arduino",
                "impressions": 20,
                "clicks": 2,
                "cost_ars": 40.0,
                "conversions": 0,
            },
        ],
    }

    mock_ga4 = MagicMock()
    mock_ga4.get_conversions.return_value = {
        "status": "success",
        "rows": [{"eventName": "whatsapp_click", "eventCount": "2", "totalUsers": "2"}],
    }
    mock_ga4.get_top_pages.return_value = {
        "status": "success",
        "rows": [
            {
                "pagePath": "/datos/maquinas",
                "pageTitle": "Telemetria",
                "screenPageViews": "25",
                "activeUsers": "15",
            }
        ],
    }
    mock_ga4.get_traffic_sources.return_value = {
        "status": "success",
        "rows": [
            {
                "sessionSource": "google",
                "sessionMedium": "cpc",
                "sessionCampaignName": "retrofit-iot",
                "sessions": "16",
                "activeUsers": "14",
                "conversions": "1.0",
            },
            {
                "sessionSource": "google",
                "sessionMedium": "organic",
                "sessionCampaignName": "(not set)",
                "sessions": "4",
                "activeUsers": "4",
                "conversions": "0.0",
            },
        ],
    }
    mock_ga4.get_geo_traffic.return_value = {
        "status": "success",
        "rows": [
            {
                "city": "Pilar",
                "region": "Buenos Aires",
                "sessions": "15",
                "activeUsers": "12",
            },
            {
                "city": "Rosario",
                "region": "Santa Fe",
                "sessions": "5",
                "activeUsers": "4",
            },
        ],
    }

    mock_clarity = MagicMock()
    mock_clarity.get_intent_recording_urls.return_value = {
        "whatsapp_click": "https://clarity.microsoft.com/recordings?filter=wa",
    }

    use_case = GenerarAnalyticsDigestUseCase(
        google_ads_port=mock_ads,
        ga4_port=mock_ga4,
        clarity_port=mock_clarity,
        budget_limit_ars=1500.0,
    )

    digest = use_case.execute(days=1, current_hour_local=12)

    assert digest.status == "success"
    assert digest.days_analyzed == 1
    assert digest.pacing_severity == "normal"
    assert digest.kpis.spent_today_ars == 450.0
    assert digest.kpis.budget_limit_ars == 1500.0
    assert digest.kpis.pacing_percent == 30.0
    assert digest.kpis.ctr_percent == 4.0
    assert len(digest.campaigns) == 1
    assert len(digest.conversions) == 1
    assert len(digest.top_pages) == 1
    assert len(digest.search_terms) == 2
    assert len(digest.traffic_sources) == 2
    assert len(digest.geo_traffic) == 2
    assert digest.channel_attribution is not None
    assert digest.channel_attribution.paid_percent == 80.0
    assert digest.channel_attribution.organic_percent == 20.0
    assert digest.geo_traffic[0].is_target_zone is True
    assert digest.geo_traffic[1].is_target_zone is False
    assert "whatsapp_click" in digest.intent_recording_urls
    assert "DataMaq Analytics Digest" in digest.resumen_markdown
    assert "Gasto Hoy" in digest.resumen_markdown
    assert "Canales de Tráfico" in digest.resumen_markdown
    assert "Top Ciudades" in digest.resumen_markdown
