"""Lógica de negocio para el servidor MCP de Google Analytics 4 (DataMaq)."""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

GA4_PROPERTY_ID: str = (os.getenv("GA4_PROPERTY_ID") or "").strip()
GOOGLE_APPLICATION_CREDENTIALS: str = (
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or ""
).strip()


def get_ga4_status() -> dict[str, Any]:
    """Retorna el estado de configuración de Google Analytics 4 en DataMaq."""
    creds_exist = bool(
        GOOGLE_APPLICATION_CREDENTIALS
        and os.path.exists(GOOGLE_APPLICATION_CREDENTIALS)
    )
    return {
        "status": "configured"
        if (GA4_PROPERTY_ID and creds_exist)
        else "missing_credentials",
        "property_id": GA4_PROPERTY_ID or "No configurado",
        "credentials_path": GOOGLE_APPLICATION_CREDENTIALS or "No configurado",
        "credentials_file_found": creds_exist,
        "site_url": "https://datamaq.com.ar",
        "message": (
            "GA4 listo para consultas."
            if (GA4_PROPERTY_ID and creds_exist)
            else "Falta configurar GA4_PROPERTY_ID y/o GOOGLE_APPLICATION_CREDENTIALS en .env."
        ),
    }


def _run_ga4_report(
    dimensions: list[str],
    metrics: list[str],
    days: int = 7,
    limit: int = 10,
) -> dict[str, Any]:
    """Ejecuta un reporte de GA4 con dimensiones y métricas especificadas."""
    if (
        not GA4_PROPERTY_ID
        or not GOOGLE_APPLICATION_CREDENTIALS
        or not os.path.exists(GOOGLE_APPLICATION_CREDENTIALS)
    ):
        return {
            "status": "missing_credentials",
            "message": "GA4_PROPERTY_ID o GOOGLE_APPLICATION_CREDENTIALS no están configurados válidamente en .env.",
            "setup_guide": "Consultar docs/analytics_and_ads.md Sección 4 para configurar la Cuenta de Servicio en GCP.",
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
            property=f"properties/{GA4_PROPERTY_ID}",
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
            "property_id": GA4_PROPERTY_ID,
            "days_analyzed": days,
            "total_rows": len(results),
            "rows": results,
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


def get_ga4_top_pages(
    days: int = 7, limit: int = 10, segment: str = "all"
) -> dict[str, Any]:
    """Obtiene las páginas más visitadas y vistas de pantalla en DataMaq.

    :param days: Ventana de días hacia atrás (default: 7).
    :param limit: Cantidad máxima de filas retornadas (default: 10).
    :param segment: Segmento analítico: 'all' (todo el sitio), 'commercial' (excluye /cursos, foco industrial/PyMEs), 'academic' (solo /cursos para alumnos).
    """
    fetch_limit = limit * 4 if segment in ("commercial", "academic") else limit
    res = _run_ga4_report(
        dimensions=["pagePath", "pageTitle"],
        metrics=["screenPageViews", "activeUsers"],
        days=days,
        limit=fetch_limit,
    )
    if res.get("status") != "success" or "rows" not in res:
        return res

    rows: list[dict[str, Any]] = res.get("rows", [])
    if segment == "commercial":
        rows = [r for r in rows if not str(r.get("pagePath", "")).startswith("/cursos")]
    elif segment == "academic":
        rows = [r for r in rows if str(r.get("pagePath", "")).startswith("/cursos")]

    res["rows"] = rows[:limit]
    res["total_rows"] = len(res["rows"])
    res["segment"] = segment
    return res


def get_ga4_traffic_sources(days: int = 7, limit: int = 10) -> dict[str, Any]:
    """Obtiene el desglose de tráfico por fuente, medio y campaña UTM (SEO, Ads, Directo)."""
    return _run_ga4_report(
        dimensions=["sessionSource", "sessionMedium", "sessionCampaignName"],
        metrics=["sessions", "activeUsers", "conversions"],
        days=days,
        limit=limit,
    )


def get_ga4_geo_traffic(days: int = 7, limit: int = 15) -> dict[str, Any]:
    """Obtiene la distribución geográfica del tráfico por ciudad y región (Pilar, Escobar, Tigre, etc.)."""
    return _run_ga4_report(
        dimensions=["city", "region"],
        metrics=["sessions", "activeUsers"],
        days=days,
        limit=limit,
    )


def get_ga4_conversions(days: int = 7) -> dict[str, Any]:
    """Obtiene el conteo de conversiones y eventos clave (generate_lead, whatsapp_click)."""
    return _run_ga4_report(
        dimensions=["eventName"],
        metrics=["eventCount", "totalUsers"],
        days=days,
        limit=20,
    )
