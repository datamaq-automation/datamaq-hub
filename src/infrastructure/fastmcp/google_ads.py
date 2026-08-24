"""Servidor MCP / Adaptador para Google Ads."""

from typing import Any

from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway
from src.infrastructure.pydantic.config import get_settings

settings = get_settings()
_gateway = GoogleAdsGateway(
    developer_token=settings.google_ads_developer_token,
    client_id=settings.google_ads_client_id,
    client_secret=settings.google_ads_client_secret,
    refresh_token=settings.google_ads_refresh_token,
    customer_id=settings.google_ads_login_customer_id,
)


def get_google_ads_status() -> dict[str, Any]:
    """Retorna el estado de las credenciales y configuración de la Google Ads API."""
    return _gateway.get_status()


def get_campaign_performance(days: int = 7) -> dict[str, Any]:
    """Obtiene el rendimiento por campaña."""
    return _gateway.get_campaign_performance(days=days)


def get_search_terms_report(days: int = 7, limit: int = 20) -> dict[str, Any]:
    """Obtiene los términos de búsqueda reales que dispararon los anuncios."""
    return _gateway.get_search_terms_report(days=days, limit=limit)


def get_daily_budget_pacing() -> dict[str, Any]:
    """Audita el gasto acumulado de hoy contra el presupuesto máximo permitido."""
    return _gateway.get_daily_budget_pacing()
