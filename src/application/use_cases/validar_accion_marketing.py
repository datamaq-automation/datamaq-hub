"""Caso de uso para validación determinística de guardrails en acciones de marketing."""

from src.application.dtos.analytics_dtos import (
    MarketingActionRequestDTO,
    MarketingActionValidationDTO,
)
from src.domain.analytics.exceptions import AnalyticsDomainException
from src.domain.analytics.services import MarketingActionGuardrailService
from src.domain.analytics.value_objects import MarketingActionType

DEFAULT_MAX_DAILY_BUDGET_ARS = 1500.0
DEFAULT_MAX_CPC_ARS = 500.0


class ValidarAccionMarketingUseCase:
    """Valida que una acción de agente cumpla las políticas duras del negocio."""

    def __init__(
        self,
        max_daily_budget_ars: float = DEFAULT_MAX_DAILY_BUDGET_ARS,
        max_cpc_ars: float = DEFAULT_MAX_CPC_ARS,
    ) -> None:
        self._max_daily_budget_ars = max_daily_budget_ars
        self._max_cpc_ars = max_cpc_ars

    def execute(
        self, request: MarketingActionRequestDTO
    ) -> MarketingActionValidationDTO:
        """Valida los parámetros de la acción solicitada."""
        try:
            action_type_enum = MarketingActionType(request.action_type)
        except ValueError:
            return MarketingActionValidationDTO(
                valid=False,
                action_type=request.action_type,
                message=f"Tipo de acción no reconocido: '{request.action_type}'.",
                params=request.params,
            )

        try:
            MarketingActionGuardrailService.validate_action(
                action_type=action_type_enum,
                params=request.params,
                max_daily_budget_ars=self._max_daily_budget_ars,
                max_cpc_ars=self._max_cpc_ars,
            )
            return MarketingActionValidationDTO(
                valid=True,
                action_type=request.action_type,
                message="Acción validada y autorizada por guardrails determinísticos.",
                params=request.params,
            )
        except AnalyticsDomainException as e:
            return MarketingActionValidationDTO(
                valid=False,
                action_type=request.action_type,
                message=str(e),
                params=request.params,
            )
