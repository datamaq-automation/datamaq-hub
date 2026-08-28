"""Tests unitarios para el caso de uso ValidarAccionMarketingUseCase."""

from src.application.dtos.analytics_dtos import MarketingActionRequestDTO
from src.application.use_cases.validar_accion_marketing import (
    ValidarAccionMarketingUseCase,
)


def test_validar_accion_marketing_valida() -> None:
    """Verifica validación exitosa de acciones dentro de norma."""
    use_case = ValidarAccionMarketingUseCase(
        max_daily_budget_ars=1500.0,
        max_cpc_ars=500.0,
    )

    req = MarketingActionRequestDTO(
        action_type="adjust_budget",
        params={"new_budget_ars": 1100.0},
    )
    result = use_case.execute(req)
    assert result.valid is True
    assert "autorizada" in result.message.lower()


def test_validar_accion_marketing_invalida_presupuesto() -> None:
    """Verifica rechazo cuando el presupuesto excede los guardrails."""
    use_case = ValidarAccionMarketingUseCase(
        max_daily_budget_ars=1500.0,
    )

    req = MarketingActionRequestDTO(
        action_type="adjust_budget",
        params={"new_budget_ars": 3000.0},
    )
    result = use_case.execute(req)
    assert result.valid is False
    assert "supera el límite" in result.message


def test_validar_accion_marketing_tipo_desconocido() -> None:
    """Verifica rechazo con tipo de acción desconocido."""
    use_case = ValidarAccionMarketingUseCase()

    req = MarketingActionRequestDTO(
        action_type="delete_all_campaigns",
        params={},
    )
    result = use_case.execute(req)
    assert result.valid is False
    assert "no reconocido" in result.message
