"""Servidor MCP / Adaptador para la ficha de Google Business Profile."""

from typing import Any

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.adapters.gateways.gbp_gateway import GoogleBusinessProfileGateway
from src.application.dtos.analytics_dtos import (
    GbpPostRequestDTO,
    GbpReviewReplyRequestDTO,
)
from src.application.use_cases.publicar_en_ficha_google import (
    PublicarEnFichaGoogleUseCase,
)
from src.infrastructure.pydantic.config import get_settings

settings = get_settings()
_cache = ApiCacheGateway(
    database_url=settings.database_url,
    ttl_by_prefix=settings.cache_ttls or None,
)
_gateway = GoogleBusinessProfileGateway(
    client_id=settings.gbp_oauth_client_id,
    client_secret=settings.gbp_oauth_client_secret,
    refresh_token=settings.gbp_refresh_token,
    account_id=settings.gbp_account_id,
    location_id=settings.gbp_location_id,
    cache=_cache,
)
_escritura_use_case = PublicarEnFichaGoogleUseCase(gbp_port=_gateway)


def get_gbp_status() -> dict[str, Any]:
    """Verifica las credenciales de Google Business Profile y lista las cuentas y la ficha configuradas."""
    return _gateway.get_status()


def get_gbp_location_info() -> dict[str, Any]:
    """Obtiene categorías, área de servicio, horario y datos de contacto de la ficha de DataMaq."""
    return _gateway.get_location_info()


def get_gbp_performance(days: int = 30) -> dict[str, Any]:
    """Consulta impresiones en Maps y Search, clics al sitio, llamadas e indicaciones de los últimos N días, con el período previo para comparar."""
    return _gateway.get_performance(days)


def get_gbp_search_keywords(months: int = 1, limit: int = 25) -> dict[str, Any]:
    """Lista los términos de búsqueda con los que los usuarios encontraron la ficha en Search o Maps."""
    return _gateway.get_search_keywords(months, limit)


def get_gbp_reviews(limit: int = 20) -> dict[str, Any]:
    """Lista las reseñas de la ficha con su puntuación y si ya fueron respondidas."""
    return _gateway.get_reviews(limit)


def create_gbp_post(
    summary: str,
    cta_url: str,
    cta_type: str = "LEARN_MORE",
    schedule_time: str | None = None,
) -> dict[str, Any]:
    """Publica en la ficha, opcionalmente programada (RFC3339). El enlace debe apuntar a datamaq.com.ar con utm_campaign=gbp."""
    return _escritura_use_case.publicar(
        GbpPostRequestDTO(
            summary=summary,
            cta_url=cta_url,
            cta_type=cta_type,
            schedule_time=schedule_time,
        )
    )


def reply_to_gbp_review(
    review_id: str, comment: str, overwrite: bool = False
) -> dict[str, Any]:
    """Responde una reseña de la ficha. Rechaza pisar una respuesta existente salvo que overwrite sea True."""
    return _escritura_use_case.responder_resena(
        GbpReviewReplyRequestDTO(
            review_id=review_id,
            comment=comment,
            overwrite=overwrite,
        )
    )
