"""Controlador agnóstico para reportes, telemetría y digest determinístico de analítica comercial."""

from typing import Any

from src.adapters.gateways.clarity_gateway import ClarityGateway
from src.adapters.gateways.ga4_gateway import GA4Gateway
from src.adapters.gateways.google_ads_gateway import GoogleAdsGateway
from src.application.dtos.analytics_dtos import (
    AnalyticsDigestResponseDTO,
    DeepSeekUsageDTO,
    LocalUsageRequestDTO,
    MarketingActionRequestDTO,
    MarketingActionValidationDTO,
    TokenUsageDTO,
    UsageResponseDTO,
)
from src.application.use_cases.generar_analytics_digest import (
    GenerarAnalyticsDigestUseCase,
)
from src.application.use_cases.validar_accion_marketing import (
    ValidarAccionMarketingUseCase,
)
from src.domain.analytics.ports import APIUsagePort


class AnalyticsController:
    """Controlador puro de analítica publicitaria, tráfico web y comportamiento de usuario."""

    def __init__(
        self,
        google_ads_gateway: GoogleAdsGateway,
        ga4_gateway: GA4Gateway,
        clarity_gateway: ClarityGateway,
        budget_limit_ars: float = 1500.0,
        api_usage_gateway: APIUsagePort | None = None,
    ) -> None:
        self._ads_gateway = google_ads_gateway
        self._ga4_gateway = ga4_gateway
        self._clarity_gateway = clarity_gateway
        self._budget_limit_ars = budget_limit_ars
        self._api_usage_gateway = api_usage_gateway
        self._digest_use_case = GenerarAnalyticsDigestUseCase(
            google_ads_port=google_ads_gateway,
            ga4_port=ga4_gateway,
            clarity_port=clarity_gateway,
            budget_limit_ars=budget_limit_ars,
        )
        self._action_validator_use_case = ValidarAccionMarketingUseCase(
            max_daily_budget_ars=budget_limit_ars,
        )

    def get_digest(
        self, days: int = 1, current_hour_local: int | None = None
    ) -> AnalyticsDigestResponseDTO:
        """Genera el digest consolidado y pre-procesado con detección de anomalías."""
        return self._digest_use_case.execute(
            days=days, current_hour_local=current_hour_local
        )

    def validate_marketing_action(
        self, request: MarketingActionRequestDTO
    ) -> MarketingActionValidationDTO:
        """Valida una acción propuesta por un agente frente a guardrails duros."""
        return self._action_validator_use_case.execute(request)

    def get_summary(self) -> dict[str, Any]:
        """Genera un resumen ejecutivo consolidado del estado de marketing y telemetría."""
        ads_pacing = self._ads_gateway.get_daily_budget_pacing()
        ads_perf = self._ads_gateway.get_campaign_performance(days=1)
        ga4_convs = self._ga4_gateway.get_conversions(days=1)
        ga4_pages = self._ga4_gateway.get_top_pages(days=1, limit=5)
        clarity_urls = self._clarity_gateway.get_intent_recording_urls()

        return {
            "status": "success",
            "service": "datamaq-analytics-hub",
            "google_ads": {
                "pacing": ads_pacing,
                "campaigns": ads_perf.get("campaigns", []),
            },
            "google_analytics_4": {
                "conversions": ga4_convs.get("rows", []),
                "top_pages": ga4_pages.get("rows", []),
            },
            "microsoft_clarity": {
                "recordings": clarity_urls,
            },
        }

    def get_ads_pacing(self) -> dict[str, Any]:
        """Audita el gasto acumulado del día contra el presupuesto límite."""
        return self._ads_gateway.get_daily_budget_pacing()

    def get_ads_campaigns(self, days: int = 7, summary: bool = True) -> dict[str, Any]:
        """Obtiene el rendimiento por campaña; con ``summary=True`` agrega métricas sin lista."""
        report = self._ads_gateway.get_campaign_performance(days=days)
        if not summary or report.get("status") != "success":
            return report

        campaigns = report.get("campaigns", [])
        impressions = sum(c.get("impressions") or 0 for c in campaigns)
        clicks = sum(c.get("clicks") or 0 for c in campaigns)
        cost_ars = sum(c.get("cost_ars") or 0.0 for c in campaigns)
        conversions = sum(c.get("conversions") or 0 for c in campaigns)
        ctr_percent = round((clicks / impressions * 100.0) if impressions else 0.0, 2)
        cpc_avg_ars = round((cost_ars / clicks) if clicks else 0.0, 2)

        return {
            "status": report.get("status"),
            "customer_id": report.get("customer_id"),
            "period_days": report.get("period_days"),
            "total_campaigns": report.get("total_campaigns", len(campaigns)),
            "summary": {
                "impressions": impressions,
                "clicks": clicks,
                "cost_ars": round(cost_ars, 2),
                "ctr_percent": ctr_percent,
                "conversions": conversions,
                "cpc_avg_ars": cpc_avg_ars,
            },
        }

    def get_ads_search_terms(self, days: int = 7, limit: int = 20) -> dict[str, Any]:
        """Obtiene los términos de búsqueda reales de usuarios."""
        return self._ads_gateway.get_search_terms_report(days=days, limit=limit)

    def get_ga4_conversions(self, days: int = 7) -> dict[str, Any]:
        """Obtiene los eventos de conversión registrados en la web."""
        return self._ga4_gateway.get_conversions(days=days)

    def get_clarity_insights(self) -> dict[str, Any]:
        """Obtiene URLs y métricas de intención de UX en Microsoft Clarity."""
        return {
            "status": "success",
            "project_id": self._clarity_gateway.clarity_id,
            "intent_recording_urls": self._clarity_gateway.get_intent_recording_urls(),
        }

    def get_api_usage(self) -> UsageResponseDTO:
        """Obtiene el balance de DeepSeek y el consumo acumulado de tokens de AGY."""
        if self._api_usage_gateway is None:
            return UsageResponseDTO(
                deepseek=DeepSeekUsageDTO(
                    is_available=False, balance=0.0, currency="USD"
                ),
                agy=TokenUsageDTO(input_tokens=0, output_tokens=0, cached_tokens=0),
            )
        data = self._api_usage_gateway.obtener_usage_consolidado()
        return UsageResponseDTO.model_validate(data)

    def guardar_usage_local(self, request: LocalUsageRequestDTO) -> None:
        """Sincroniza y guarda el consumo local de tokens en el gateway."""
        if self._api_usage_gateway is not None:
            self._api_usage_gateway.guardar_usage_local(
                input_tokens=request.input_tokens,
                output_tokens=request.output_tokens,
                cached_tokens=request.cached_tokens,
            )
