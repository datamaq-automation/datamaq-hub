"""Gateway para interactuar con la Google Analytics 4 Data API."""

import os
from typing import Any

try:
    from google.api_core.exceptions import GoogleAPICallError
except ImportError:
    # google-api-core ausente en entornos de test/CI sin dependencias de Google
    GoogleAPICallError = Exception

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.domain.cache.ports import ApiCachePort


def _run_ga4_report(
    ga4_property_id: str,
    google_application_credentials: str,
    dimensions: list[str],
    metrics: list[str],
    days: int = 7,
    limit: int = 10,
) -> dict[str, Any]:
    """Ejecuta un reporte de GA4 con dimensiones y métricas especificadas."""
    if (
        not ga4_property_id
        or not google_application_credentials
        or not os.path.exists(google_application_credentials)
    ):
        return {
            "status": "missing_credentials",
            "message": "GA4_PROPERTY_ID o GOOGLE_APPLICATION_CREDENTIALS no están configurados válidamente en .env.",
            "setup_guide": "Consultar docs/credenciales_entornos.md Sección 4 (diagnóstico y reposición de la credencial) y docs/analytics_and_ads.md Sección 2 (mapa de variables).",
        }

    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient  # type: ignore
        from google.analytics.data_v1beta.types import (  # type: ignore
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )

        client = BetaAnalyticsDataClient()
        request = RunReportRequest(
            property=f"properties/{ga4_property_id}",
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            date_ranges=[DateRange(start_date=f"{days}daysAgo", end_date="today")],
            limit=limit,
        )
        response = client.run_report(request)

        results: list[dict[str, Any]] = []
        for row in response.rows:
            row_dict: dict[str, Any] = {}
            for i, dim_val in enumerate(row.dimension_values):
                row_dict[dimensions[i]] = dim_val.value
            for j, metric_val in enumerate(row.metric_values):
                row_dict[metrics[j]] = metric_val.value
            results.append(row_dict)

        return {
            "status": "success",
            "property_id": ga4_property_id,
            "days_analyzed": days,
            "total_rows": len(results),
            "rows": results,
        }
    except ImportError as e:
        return {"status": "error", "message": str(e)}
    except GoogleAPICallError as e:
        return {"status": "error", "message": str(e)}


class GA4Gateway:
    """Encapsula llamadas I/O a Google Analytics 4 sin acoplamiento a infraestructura."""

    def __init__(
        self,
        ga4_property_id: str,
        google_application_credentials: str,
        cache: ApiCachePort | None = None,
    ):
        self.ga4_property_id = ga4_property_id.strip()
        self.google_application_credentials = google_application_credentials.strip()
        self._cache: ApiCachePort = cache if cache is not None else ApiCacheGateway()

    def get_status(self) -> dict[str, Any]:
        """Retorna el estado de configuración de Google Analytics 4 en DataMaq."""
        creds_exist = bool(
            self.google_application_credentials
            and os.path.exists(self.google_application_credentials)
        )
        return {
            "status": "configured"
            if (self.ga4_property_id and creds_exist)
            else "missing_credentials",
            "property_id": self.ga4_property_id or "No configurado",
            "credentials_path": self.google_application_credentials or "No configurado",
            "credentials_file_found": creds_exist,
            "site_url": "https://datamaq.com.ar",
            "message": (
                "GA4 listo para consultas."
                if (self.ga4_property_id and creds_exist)
                else "Falta configurar GA4_PROPERTY_ID y/o GOOGLE_APPLICATION_CREDENTIALS en .env."
            ),
        }

    def get_top_pages(
        self, days: int = 7, limit: int = 10, segment: str = "all"
    ) -> dict[str, Any]:
        """Obtiene las páginas más visitadas y vistas de pantalla en DataMaq."""
        key = f"ga4:top_pages:days_{days}:limit_{limit}:segment_{segment}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        fetch_limit = limit * 4 if segment in ("commercial", "academic") else limit
        res = _run_ga4_report(
            self.ga4_property_id,
            self.google_application_credentials,
            dimensions=["pagePath", "pageTitle"],
            metrics=["screenPageViews", "activeUsers"],
            days=days,
            limit=fetch_limit,
        )
        if res.get("status") != "success" or "rows" not in res:
            return res

        rows: list[dict[str, Any]] = res.get("rows", [])
        if segment == "commercial":
            rows = [
                r for r in rows if not str(r.get("pagePath", "")).startswith("/cursos")
            ]
        elif segment == "academic":
            rows = [r for r in rows if str(r.get("pagePath", "")).startswith("/cursos")]

        res["rows"] = rows[:limit]
        res["total_rows"] = len(res["rows"])
        res["segment"] = segment
        self._cache.set(key, res)
        return res

    def get_traffic_sources(self, days: int = 7, limit: int = 10) -> dict[str, Any]:
        """Obtiene el desglose de tráfico por fuente, medio y campaña UTM (SEO, Ads, Directo)."""
        key = f"ga4:traffic_sources:days_{days}:limit_{limit}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = _run_ga4_report(
            self.ga4_property_id,
            self.google_application_credentials,
            dimensions=["sessionSource", "sessionMedium", "sessionCampaignName"],
            metrics=["sessions", "activeUsers", "conversions"],
            days=days,
            limit=limit,
        )
        if result.get("status") == "success":
            self._cache.set(key, result)
        return result

    def get_geo_traffic(self, days: int = 7, limit: int = 15) -> dict[str, Any]:
        """Obtiene la distribución geográfica del tráfico por ciudad y región (Pilar, Escobar, Tigre, etc.)."""
        key = f"ga4:geo_traffic:days_{days}:limit_{limit}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = _run_ga4_report(
            self.ga4_property_id,
            self.google_application_credentials,
            dimensions=["city", "region"],
            metrics=["sessions", "activeUsers"],
            days=days,
            limit=limit,
        )
        if result.get("status") == "success":
            self._cache.set(key, result)
        return result

    def get_conversions(self, days: int = 7) -> dict[str, Any]:
        """Obtiene el conteo de conversiones y eventos clave (generate_lead, whatsapp_click)."""
        key = f"ga4:conversions:days_{days}"
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        result = _run_ga4_report(
            self.ga4_property_id,
            self.google_application_credentials,
            dimensions=["eventName"],
            metrics=["eventCount", "totalUsers"],
            days=days,
            limit=20,
        )
        if result.get("status") == "success":
            self._cache.set(key, result)
        return result
