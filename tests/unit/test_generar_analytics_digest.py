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


def _puertos_vacios() -> tuple[MagicMock, MagicMock, MagicMock]:
    """Puertos Ads/GA4/Clarity que devuelven respuestas vacías pero válidas."""
    mock_ads = MagicMock()
    mock_ads.get_daily_budget_pacing.return_value = {
        "status": "success",
        "spent_ars": 0.0,
    }
    mock_ads.get_campaign_performance.return_value = {
        "status": "success",
        "campaigns": [],
    }
    mock_ads.get_search_terms_report.return_value = {"status": "success", "terms": []}

    mock_ga4 = MagicMock()
    mock_ga4.get_conversions.return_value = {"status": "success", "rows": []}
    mock_ga4.get_top_pages.return_value = {"status": "success", "rows": []}
    mock_ga4.get_traffic_sources.return_value = {"status": "success", "rows": []}
    mock_ga4.get_geo_traffic.return_value = {"status": "success", "rows": []}

    mock_clarity = MagicMock()
    mock_clarity.get_intent_recording_urls.return_value = {}

    return mock_ads, mock_ga4, mock_clarity


def test_digest_sin_puerto_gbp_sigue_funcionando() -> None:
    """Retrocompatibilidad: el digest debe funcionar sin ficha configurada."""
    mock_ads, mock_ga4, mock_clarity = _puertos_vacios()

    dto = GenerarAnalyticsDigestUseCase(
        google_ads_port=mock_ads,
        ga4_port=mock_ga4,
        clarity_port=mock_clarity,
    ).execute(days=1)

    assert dto.status == "success"
    assert dto.ficha_resumen is None
    assert dto.ficha_resenas == []
    assert dto.ficha_terminos == []
    assert "Ficha de Google" not in dto.resumen_markdown


def test_digest_incorpora_la_ficha_de_google() -> None:
    """La ficha aporta resumen, reseñas, términos y sus propias anomalías."""
    mock_ads, mock_ga4, mock_clarity = _puertos_vacios()

    mock_gbp = MagicMock()
    mock_gbp.get_performance.return_value = {
        "status": "success",
        "dias_analizados": 28,
        "metricas": [
            {
                "fecha": "2026-08-01",
                "metrica": "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
                "valor": 60,
            },
            {
                "fecha": "2026-08-01",
                "metrica": "BUSINESS_IMPRESSIONS_MOBILE_SEARCH",
                "valor": 40,
            },
            {"fecha": "2026-08-01", "metrica": "WEBSITE_CLICKS", "valor": 9},
        ],
        "metricas_periodo_previo": [
            {
                "fecha": "2026-07-01",
                "metrica": "BUSINESS_IMPRESSIONS_MOBILE_MAPS",
                "valor": 200,
            },
        ],
    }
    mock_gbp.get_reviews.return_value = {
        "status": "success",
        "resenas": [
            {
                "review_id": "r1",
                "autor": "Planta A",
                "estrellas": 5,
                "comentario": "Muy bien",
                "fecha_utc": "2026-08-01T00:00:00Z",
                "tiene_respuesta": False,
            }
        ],
    }
    mock_gbp.get_search_keywords.return_value = {
        "status": "success",
        "terminos": [
            {"termino": "datamaq", "impresiones": 20},
            {"termino": "correccion factor de potencia garin", "impresiones": 80},
        ],
    }

    dto = GenerarAnalyticsDigestUseCase(
        google_ads_port=mock_ads,
        ga4_port=mock_ga4,
        clarity_port=mock_clarity,
        gbp_port=mock_gbp,
    ).execute(days=1)

    assert dto.ficha_resumen is not None
    assert dto.ficha_resumen.impresiones_totales == 100
    assert dto.ficha_resumen.variacion_impresiones_percent == -50.0
    assert len(dto.ficha_resenas) == 1
    assert [t.es_de_marca for t in dto.ficha_terminos] == [True, False]

    tipos = {a.anomaly_type for a in dto.anomalies}
    assert "ficha_impresiones_en_caida" in tipos
    assert "ficha_resena_sin_responder" in tipos

    assert "Ficha de Google" in dto.resumen_markdown
    assert "Top descubrimiento" in dto.resumen_markdown

    # La ficha se lee sobre ventana mensual aunque el digest pida 1 día.
    mock_gbp.get_performance.assert_called_once_with(days=28)


def test_digest_degrada_si_la_api_de_la_ficha_no_esta_aprobada() -> None:
    """Con quota 0 QPM la ficha no aporta datos, pero el digest no se rompe."""
    mock_ads, mock_ga4, mock_clarity = _puertos_vacios()

    mock_gbp = MagicMock()
    no_aprobada = {"status": "api_not_approved", "message": "quota 0"}
    mock_gbp.get_performance.return_value = no_aprobada
    mock_gbp.get_reviews.return_value = no_aprobada
    mock_gbp.get_search_keywords.return_value = no_aprobada

    dto = GenerarAnalyticsDigestUseCase(
        google_ads_port=mock_ads,
        ga4_port=mock_ga4,
        clarity_port=mock_clarity,
        gbp_port=mock_gbp,
    ).execute(days=1)

    assert dto.status == "success"
    assert dto.ficha_resumen is None
    assert dto.ficha_resenas == []
