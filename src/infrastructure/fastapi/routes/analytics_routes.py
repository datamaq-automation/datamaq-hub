"""FastAPI routing para endpoints de analítica, telemetría y digest determinístico."""

from functools import lru_cache
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query

from src.adapters.controllers.analytics_controller import AnalyticsController
from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway
from src.application.dtos.analytics_dtos import (
    AnalyticsDigestResponseDTO,
    MarketingActionRequestDTO,
    MarketingActionValidationDTO,
)
from src.application.dtos.common_dto import APIResponseDTO
from src.infrastructure.pydantic.config import get_settings

router = APIRouter(prefix="/analytics", tags=["Analytics & Telemetry"])


@lru_cache
def get_analytics_controller() -> AnalyticsController:
    """Proveedor de dependencias para AnalyticsController con gateways configurados."""
    settings = get_settings()
    cache = ApiCacheGateway(
        database_url=settings.database_url,
        ttl_by_prefix=settings.cache_ttls or None,
    )
    ads_gateway = GoogleAdsGateway(
        developer_token=settings.google_ads_developer_token,
        client_id=settings.google_ads_client_id,
        client_secret=settings.google_ads_client_secret,
        refresh_token=settings.google_ads_refresh_token,
        customer_id=settings.google_ads_login_customer_id,
        cache=cache,
    )
    ga4_gateway = GA4Gateway(
        ga4_property_id=settings.ga4_property_id,
        google_application_credentials=settings.google_application_credentials,
        cache=cache,
    )
    clarity_gateway = ClarityGateway(
        clarity_id=settings.clarity_id,
        clarity_api_token=settings.clarity_api_token,
        cache=cache,
    )
    return AnalyticsController(
        google_ads_gateway=ads_gateway,
        ga4_gateway=ga4_gateway,
        clarity_gateway=clarity_gateway,
        budget_limit_ars=1500.0,
    )


@router.get(
    "/digest",
    response_model=APIResponseDTO[AnalyticsDigestResponseDTO],
    summary="Digest Pre-procesado de Analítica (OpenClaw / Telegram)",
    description=(
        "Retorna un resumen estructurado, comprimido y enriquecido con detección "
        "determinística de anomalías, cálculo de KPIs exactos y reducción de tokens para agentes."
    ),
)
async def get_analytics_digest(
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
    days: int = Query(1, ge=1, le=90, description="Días hacia atrás a analizar"),
) -> APIResponseDTO[AnalyticsDigestResponseDTO]:
    """Genera el digest pre-procesado para consumo inteligente."""
    result = controller.get_digest(days=days)
    return APIResponseDTO[AnalyticsDigestResponseDTO](success=True, data=result)


@router.post(
    "/actions/validate",
    response_model=APIResponseDTO[MarketingActionValidationDTO],
    summary="Validación Determinística de Acciones de Agentes (Guardrails)",
    description=(
        "Valida que una acción de marketing propuesta por un agente autónomo "
        "cumpla con las políticas de seguridad y límites de presupuesto ($1.500 ARS/día)."
    ),
)
async def validate_marketing_action(
    request: MarketingActionRequestDTO,
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
) -> APIResponseDTO[MarketingActionValidationDTO]:
    """Evalúa los guardrails duros de post-procesamiento."""
    result = controller.validate_marketing_action(request)
    return APIResponseDTO[MarketingActionValidationDTO](success=True, data=result)


@router.get(
    "/summary",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Resumen Ejecutivo de Analítica y Marketing",
    description="Retorna el estado consolidado de Google Ads, conversiones de GA4 y sesiones UX de Clarity.",
)
async def get_analytics_summary(
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
) -> APIResponseDTO[dict[str, Any]]:
    """Genera el resumen de telemetría y marketing en tiempo real."""
    result = controller.get_summary()
    return APIResponseDTO[dict[str, Any]](success=True, data=result)


@router.get(
    "/ads/pacing",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Pacing de Presupuesto Diario Google Ads",
    description="Audita el gasto acumulado de hoy contra el límite de seguridad de $1.500 ARS/día.",
)
async def get_ads_budget_pacing(
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
) -> APIResponseDTO[dict[str, Any]]:
    """Retorna el gasto de hoy y porcentaje del presupuesto diario."""
    result = controller.get_ads_pacing()
    return APIResponseDTO[dict[str, Any]](success=True, data=result)


@router.get(
    "/ads/campaigns",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Rendimiento de Campañas Google Ads",
    description="Obtiene impresiones, clics, costos y conversiones por campaña para un período de días.",
)
async def get_ads_campaigns(
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
    days: int = Query(7, ge=1, le=90, description="Días hacia atrás a analizar"),
) -> APIResponseDTO[dict[str, Any]]:
    """Retorna el reporte de rendimiento por campaña."""
    result = controller.get_ads_campaigns(days=days)
    return APIResponseDTO[dict[str, Any]](success=True, data=result)


@router.get(
    "/ads/search-terms",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Términos de Búsqueda Reales",
    description="Obtiene los términos de búsqueda que activaron los anuncios para identificar oportunidades o palabras negativas.",
)
async def get_ads_search_terms(
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
    days: int = Query(7, ge=1, le=90, description="Días hacia atrás a analizar"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de términos"),
) -> APIResponseDTO[dict[str, Any]]:
    """Retorna el reporte de términos de búsqueda."""
    result = controller.get_ads_search_terms(days=days, limit=limit)
    return APIResponseDTO[dict[str, Any]](success=True, data=result)


@router.get(
    "/ga4/conversions",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Conversiones Web de GA4",
    description="Retorna el conteo de eventos clave (WhatsApp, formulario de contacto, llamadas) en la web.",
)
async def get_ga4_conversions(
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
    days: int = Query(7, ge=1, le=90, description="Días hacia atrás a analizar"),
) -> APIResponseDTO[dict[str, Any]]:
    """Retorna el reporte de conversiones de GA4."""
    result = controller.get_ga4_conversions(days=days)
    return APIResponseDTO[dict[str, Any]](success=True, data=result)


@router.get(
    "/clarity/live",
    response_model=APIResponseDTO[dict[str, Any]],
    summary="Grabaciones UX de Microsoft Clarity",
    description="Retorna el mapa de URLs filtradas a grabaciones de usuarios con alta intención comercial.",
)
async def get_clarity_live_insights(
    controller: Annotated[AnalyticsController, Depends(get_analytics_controller)],
) -> APIResponseDTO[dict[str, Any]]:
    """Retorna enlaces directos a grabaciones de UX."""
    result = controller.get_clarity_insights()
    return APIResponseDTO[dict[str, Any]](success=True, data=result)
