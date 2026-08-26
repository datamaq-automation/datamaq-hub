"""Servidor MCP / Adaptador para Microsoft Clarity."""

from typing import Any

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.infrastructure.pydantic.config import get_settings

settings = get_settings()
_cache = ApiCacheGateway(
    database_url=settings.database_url,
    ttl_by_prefix=settings.cache_ttls or None,
)
_gateway = ClarityGateway(
    clarity_id=settings.clarity_id,
    clarity_api_token=settings.clarity_api_token,
    cache=_cache,
)


def get_clarity_project_info() -> dict[str, Any]:
    """Obtiene la información del proyecto Microsoft Clarity configurado para DataMaq."""
    return _gateway.get_project_info()


def get_live_insights() -> dict[str, Any]:
    """Consulta los usuarios activos y páginas vistas en tiempo real en DataMaq."""
    return _gateway.get_live_insights()


def get_dashboard_insights(num_of_days: int = 3) -> dict[str, Any]:
    """Obtiene las métricas agregadas de comportamiento de los últimos N días."""
    return _gateway.get_dashboard_insights(num_of_days)
