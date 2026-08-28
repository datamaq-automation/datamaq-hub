"""Controlador agnóstico de transporte para herramientas de cálculo y utilidades de ingeniería."""

from src.application.dtos.calculadora_cos_fi_dtos import (
    CalculoCosFiRequestDTO,
    CalculoCosFiResponseDTO,
)
from src.application.use_cases.calcular_recargo_cos_fi import (
    CalcularRecargoCosFiUseCase,
)


class ToolsController:
    """Controlador para herramientas técnicas, simuladores y calculadoras industriales."""

    def __init__(
        self,
        calcular_cos_fi_use_case: CalcularRecargoCosFiUseCase | None = None,
    ) -> None:
        self._calcular_cos_fi_use_case = (
            calcular_cos_fi_use_case or CalcularRecargoCosFiUseCase()
        )

    def calcular_cos_fi(
        self, request: CalculoCosFiRequestDTO
    ) -> CalculoCosFiResponseDTO:
        """Calcula la penalidad tarifaria y dimensión de banco de capacitores."""
        return self._calcular_cos_fi_use_case.execute(request)
