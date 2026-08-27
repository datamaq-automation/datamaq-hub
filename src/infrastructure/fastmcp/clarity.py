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


def get_intent_recording_urls() -> dict[str, str]:
    """Retorna los enlaces web directos a grabaciones de Clarity filtradas por eventos de conversión (email_click, whatsapp_click, form_submit, etc.)."""
    return _gateway.get_intent_recording_urls()


def get_recording_url(filter_tag: str = "") -> str:
    """Genera la URL directa a grabaciones de Clarity para un tag de conversión o filtro personalizado."""
    return _gateway.get_recording_url(filter_tag if filter_tag else None)
