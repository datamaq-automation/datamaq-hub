"""Lógica de negocio para el servidor MCP de Google Ads (DataMaq)."""

import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()

DEVELOPER_TOKEN: str = (os.getenv("GOOGLE_ADS_DEVELOPER_TOKEN") or "").strip()
CLIENT_ID: str = (os.getenv("GOOGLE_ADS_CLIENT_ID") or "").strip()
CLIENT_SECRET: str = (os.getenv("GOOGLE_ADS_CLIENT_SECRET") or "").strip()
REFRESH_TOKEN: str = (os.getenv("GOOGLE_ADS_REFRESH_TOKEN") or "").strip()
CUSTOMER_ID: str = (os.getenv("GOOGLE_ADS_LOGIN_CUSTOMER_ID") or "1318780733").replace("-", "").strip()

DAILY_BUDGET_LIMIT_ARS: float = 1500.0


def get_google_ads_status() -> dict[str, Any]:
    """Retorna el estado de las credenciales y configuración de la Google Ads API."""
    is_ready = bool(DEVELOPER_TOKEN and CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN and CUSTOMER_ID)

    accessible_accounts: list[str] = []
    token_level = "unknown"
    if is_ready:
        try:
            client = _get_google_ads_client()
            if client:
                customer_service = client.get_service("CustomerService")
                resp = customer_service.list_accessible_customers()
                accessible_accounts = [r.replace("customers/", "") for r in resp.resource_names]
                token_level = "test_or_basic_active"
        except Exception as e:
            if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
                token_level = "test_access_only (requiere solicitar Acceso Básico en Google Ads API Center)"
            else:
                token_level = f"error: {str(e)[:100]}"

    return {
        "status": "ready" if is_ready else "pending_credentials",
        "has_developer_token": bool(DEVELOPER_TOKEN),
        "has_client_id": bool(CLIENT_ID),
        "has_client_secret": bool(CLIENT_SECRET),
        "has_refresh_token": bool(REFRESH_TOKEN),
        "customer_id": CUSTOMER_ID or "No configurado",
        "accessible_accounts": accessible_accounts,
        "developer_token_level": token_level,
        "daily_budget_limit_ars": DAILY_BUDGET_LIMIT_ARS,
        "message": (
            "Google Ads API conectada con éxito."
            if is_ready
            else "Falta completar GOOGLE_ADS_REFRESH_TOKEN o GOOGLE_ADS_LOGIN_CUSTOMER_ID en .env."
        ),
    }


def _get_google_ads_client() -> Any:
    """Inicializa y retorna un cliente de la Google Ads API."""
    if not (DEVELOPER_TOKEN and CLIENT_ID and CLIENT_SECRET and REFRESH_TOKEN):
        return None

    try:
        from google.ads.googleads.client import GoogleAdsClient  # type: ignore

        credentials: dict[str, Any] = {
            "developer_token": DEVELOPER_TOKEN,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": REFRESH_TOKEN,
            "use_proto_plus": True,
        }
        return GoogleAdsClient.load_from_dict(credentials)
    except Exception:
        return None


def get_campaign_performance(days: int = 7) -> dict[str, Any]:
    """Obtiene el rendimiento por campaña (impresiones, clics, costo ARS, conversiones, CPC promedio)."""
    status = get_google_ads_status()
    if status["status"] != "ready":
        return {
            "status": "missing_credentials",
            "details": status,
            "instructions": "Correr 'scripts/auth_google_ads.py' para generar el Refresh Token.",
        }

    client = _get_google_ads_client()
    if not client:
        return {"status": "error", "message": "No se pudo inicializar GoogleAdsClient."}

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            campaign.id,
            campaign.name,
            campaign.status,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions,
            metrics.average_cpc
        FROM campaign
        WHERE segments.date DURING LAST_{days}_DAYS
        ORDER BY metrics.clicks DESC
    """

    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        campaigns: list[dict[str, Any]] = []
        total_cost_ars = 0.0

        for row in response:
            cost_ars = (row.metrics.cost_micros or 0) / 1_000_000.0
            avg_cpc_ars = (row.metrics.average_cpc or 0) / 1_000_000.0
            total_cost_ars += cost_ars
            campaigns.append(
                {
                    "id": str(row.campaign.id),
                    "name": row.campaign.name,
                    "status": str(row.campaign.status.name),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost_ars": round(cost_ars, 2),
                    "avg_cpc_ars": round(avg_cpc_ars, 2),
                    "conversions": row.metrics.conversions,
                }
            )

        return {
            "status": "success",
            "customer_id": CUSTOMER_ID,
            "period_days": days,
            "total_campaigns": len(campaigns),
            "total_cost_ars": round(total_cost_ars, 2),
            "campaigns": campaigns,
        }
    except Exception as e:
        if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
            return {
                "status": "developer_token_test_access",
                "message": "El Developer Token actual está en nivel 'Test Access'. Para leer cuentas reales de producción, solicitar 'Acceso Básico' en Google Ads -> Herramientas -> Centro de la API.",
                "customer_id": CUSTOMER_ID,
            }
        return {"status": "error", "message": str(e)}


def get_search_terms_report(days: int = 7, limit: int = 20) -> dict[str, Any]:
    """Obtiene los términos de búsqueda reales que dispararon los anuncios para identificar negativas."""
    status = get_google_ads_status()
    if status["status"] != "ready":
        return {"status": "missing_credentials", "details": status}

    client = _get_google_ads_client()
    if not client:
        return {"status": "error", "message": "No se pudo inicializar GoogleAdsClient."}

    ga_service = client.get_service("GoogleAdsService")
    query = f"""
        SELECT
            search_term_view.search_term,
            campaign.name,
            metrics.impressions,
            metrics.clicks,
            metrics.cost_micros,
            metrics.conversions
        FROM search_term_view
        WHERE segments.date DURING LAST_{days}_DAYS
        ORDER BY metrics.clicks DESC
        LIMIT {limit}
    """

    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        terms: list[dict[str, Any]] = []
        for row in response:
            terms.append(
                {
                    "search_term": row.search_term_view.search_term,
                    "campaign": row.campaign.name,
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost_ars": round((row.metrics.cost_micros or 0) / 1_000_000.0, 2),
                    "conversions": row.metrics.conversions,
                }
            )
        return {"status": "success", "terms": terms}
    except Exception as e:
        if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
            return {
                "status": "developer_token_test_access",
                "message": "El Developer Token actual está en nivel 'Test Access'. Solicitar 'Acceso Básico' en Centro de la API de Google Ads.",
            }
        return {"status": "error", "message": str(e)}


def get_daily_budget_pacing() -> dict[str, Any]:
    """Audita el gasto acumulado de hoy contra el presupuesto máximo permitido de $1.500 ARS/día."""
    status = get_google_ads_status()
    if status["status"] != "ready":
        return {
            "status": "missing_credentials",
            "daily_limit_ars": DAILY_BUDGET_LIMIT_ARS,
            "rule": "Límite máximo de gasto: $1.500 ARS/día",
        }

    client = _get_google_ads_client()
    if not client:
        return {"status": "error", "message": "No se pudo inicializar GoogleAdsClient."}

    ga_service = client.get_service("GoogleAdsService")
    query = """
        SELECT
            metrics.cost_micros,
            metrics.clicks,
            metrics.impressions
        FROM customer
        WHERE segments.date DURING TODAY
    """

    try:
        response = ga_service.search(customer_id=CUSTOMER_ID, query=query)
        today_cost_ars = 0.0
        today_clicks = 0
        for row in response:
            today_cost_ars += (row.metrics.cost_micros or 0) / 1_000_000.0
            today_clicks += row.metrics.clicks or 0

        pacing_percentage = (today_cost_ars / DAILY_BUDGET_LIMIT_ARS) * 100.0
        is_safe = today_cost_ars <= DAILY_BUDGET_LIMIT_ARS

        return {
            "status": "success",
            "date": "TODAY",
            "spent_ars": round(today_cost_ars, 2),
            "daily_budget_limit_ars": DAILY_BUDGET_LIMIT_ARS,
            "pacing_percentage": f"{round(pacing_percentage, 1)}%",
            "is_within_budget": is_safe,
            "clicks_today": today_clicks,
            "alert": "Presupuesto OK" if is_safe else "ALERTA: Presupuesto diario excedido",
        }
    except Exception as e:
        if "DEVELOPER_TOKEN_NOT_APPROVED" in str(e):
            return {
                "status": "developer_token_test_access",
                "message": "Developer Token en Test Access. Límite configurado: $1.500 ARS/día.",
                "daily_budget_limit_ars": DAILY_BUDGET_LIMIT_ARS,
            }
        return {"status": "error", "message": str(e)}
