"""Servidor MCP / Adaptador para Google Analytics 4."""

from typing import Any

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.infrastructure.pydantic.config import get_settings

settings = get_settings()
_cache = ApiCacheGateway(
    database_url=settings.database_url,
    ttl_by_prefix=settings.cache_ttls or None,
)
_gateway = GA4Gateway(
    ga4_property_id=settings.ga4_property_id,
    google_application_credentials=settings.google_application_credentials,
    cache=_cache,
)


def get_ga4_status() -> dict[str, Any]:
    """Retorna el estado de configuración de Google Analytics 4 en DataMaq."""
    return _gateway.get_status()


def get_ga4_top_pages(
    days: int = 7, limit: int = 10, segment: str = "all"
) -> dict[str, Any]:
    """Obtiene las páginas más visitadas y vistas de pantalla en DataMaq."""
    return _gateway.get_top_pages(days=days, limit=limit, segment=segment)


def get_ga4_traffic_sources(days: int = 7, limit: int = 10) -> dict[str, Any]:
    """Obtiene el desglose de tráfico por fuente, medio y campaña UTM."""
    return _gateway.get_traffic_sources(days=days, limit=limit)


def get_ga4_geo_traffic(days: int = 7, limit: int = 15) -> dict[str, Any]:
    """Obtiene la distribución geográfica del tráfico por ciudad y región."""
    return _gateway.get_geo_traffic(days=days, limit=limit)


def get_ga4_conversions(days: int = 7) -> dict[str, Any]:
    """Obtiene el conteo de conversiones y eventos clave."""
    return _gateway.get_conversions(days=days)
