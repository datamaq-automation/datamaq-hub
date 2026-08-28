"""Adaptador FastMCP para el Digest consolidado y guardrails de marketing."""

from typing import Any

from src.adapters.gateways.api_cache_gateway import ApiCacheGateway
from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway
from src.application.dtos.analytics_dtos import MarketingActionRequestDTO
from src.application.use_cases.generar_analytics_digest import (
    GenerarAnalyticsDigestUseCase,
)
from src.application.use_cases.validar_accion_marketing import (
    ValidarAccionMarketingUseCase,
)
from src.infrastructure.pydantic.config import get_settings

settings = get_settings()
_cache = ApiCacheGateway(
    database_url=settings.database_url,
    ttl_by_prefix=settings.cache_ttls or None,
)
_ads_gw = GoogleAdsGateway(
    developer_token=settings.google_ads_developer_token,
    client_id=settings.google_ads_client_id,
    client_secret=settings.google_ads_client_secret,
    refresh_token=settings.google_ads_refresh_token,
    customer_id=settings.google_ads_login_customer_id,
    cache=_cache,
)
_ga4_gw = GA4Gateway(
    ga4_property_id=settings.ga4_property_id,
    google_application_credentials=settings.google_application_credentials,
    cache=_cache,
)
_clarity_gw = ClarityGateway(
    clarity_id=settings.clarity_id,
    clarity_api_token=settings.clarity_api_token,
    cache=_cache,
)

_digest_use_case = GenerarAnalyticsDigestUseCase(
    google_ads_port=_ads_gw,
    ga4_port=_ga4_gw,
    clarity_port=_clarity_gw,
    budget_limit_ars=1500.0,
)
_validator_use_case = ValidarAccionMarketingUseCase(
    max_daily_budget_ars=1500.0,
)


def get_analytics_digest(days: int = 1) -> dict[str, Any]:
    """Retorna el resumen pre-procesado, KPIs calculados, anomalías y grabaciones de intención."""
    dto = _digest_use_case.execute(days=days)
    return dto.model_dump()


def validate_marketing_action(
    action_type: str, params: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Evalúa los guardrails determinísticos de una acción propuesta por el agente."""
    req = MarketingActionRequestDTO(
        action_type=action_type,
        params=params or {},
    )
    res = _validator_use_case.execute(req)
    return res.model_dump()
