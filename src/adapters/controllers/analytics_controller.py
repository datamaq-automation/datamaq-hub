"""Controlador agnóstico para reportes y telemetría de analítica comercial (Google Ads, GA4, Clarity)."""

from typing import Any

from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway


class AnalyticsController:
    """Controlador puro de analítica publicitaria, tráfico web y comportamiento de usuario."""

    def __init__(
        self,
        google_ads_gateway: GoogleAdsGateway,
        ga4_gateway: GA4Gateway,
        clarity_gateway: ClarityGateway,
    ) -> None:
        self._ads_gateway = google_ads_gateway
        self._ga4_gateway = ga4_gateway
        self._clarity_gateway = clarity_gateway

    def get_summary(self) -> dict[str, Any]:
        """Genera un resumen ejecutivo consolidado del estado de marketing y telemetría."""
        ads_pacing = self._ads_gateway.get_daily_budget_pacing()
        ads_perf = self._ads_gateway.get_campaign_performance(days=1)
        ga4_convs = self._ga4_gateway.get_conversions(days=1)
        ga4_pages = self._ga4_gateway.get_top_pages(days=1, limit=5)
        clarity_urls = self._clarity_gateway.get_intent_recording_urls()

        return {
            "status": "success",
            "service": "datamaq-analytics-hub",
            "google_ads": {
                "pacing": ads_pacing,
                "campaigns": ads_perf.get("campaigns", []),
            },
            "google_analytics_4": {
                "conversions": ga4_convs.get("rows", []),
                "top_pages": ga4_pages.get("rows", []),
            },
            "microsoft_clarity": {
                "recordings": clarity_urls,
            },
        }

    def get_ads_pacing(self) -> dict[str, Any]:
        """Audita el gasto acumulado del día contra el presupuesto límite."""
        return self._ads_gateway.get_daily_budget_pacing()

    def get_ads_campaigns(self, days: int = 7) -> dict[str, Any]:
        """Obtiene el rendimiento histórico por campaña."""
        return self._ads_gateway.get_campaign_performance(days=days)

    def get_ads_search_terms(self, days: int = 7, limit: int = 20) -> dict[str, Any]:
        """Obtiene los términos de búsqueda reales de usuarios."""
        return self._ads_gateway.get_search_terms_report(days=days, limit=limit)

    def get_ga4_conversions(self, days: int = 7) -> dict[str, Any]:
        """Obtiene los eventos de conversión registrados en la web."""
        return self._ga4_gateway.get_conversions(days=days)

    def get_clarity_insights(self) -> dict[str, Any]:
        """Obtiene URLs y métricas de intención de UX en Microsoft Clarity."""
        return {
            "status": "success",
            "project_id": self._clarity_gateway.clarity_id,
            "intent_recording_urls": self._clarity_gateway.get_intent_recording_urls(),
        }
