"""FastAPI routes para herramientas interactivas, calculadoras y utilidades de ingeniería."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.adapters.controllers.dependencies import get_tools_controller
from src.adapters.controllers.tools_controller import ToolsController
from src.application.dtos.calculadora_cos_fi_dtos import (
    CalculoCosFiRequestDTO,
    CalculoCosFiResponseDTO,
)
from src.application.dtos.common_dto import APIResponseDTO

router = APIRouter(prefix="/tools", tags=["Engineering Tools & Calculators"])


@router.post(
    "/calculadora-cos-fi",
    response_model=APIResponseDTO[CalculoCosFiResponseDTO],
    summary="Calculadora de Factor de Potencia cos φ y Multas Edenor/Edesur",
    description=(
        "Calcula determinísticamente el recargo tarifario según cuadro ENRE, "
        "la potencia reactiva (kVAr) requerida y el banco de capacitores comercial "
        "recomendado para anular la penalidad."
    ),
)
async def calcular_factor_de_potencia_cos_fi(
    request: CalculoCosFiRequestDTO,
    controller: Annotated[ToolsController, Depends(get_tools_controller)],
) -> APIResponseDTO[CalculoCosFiResponseDTO]:
    """Ejecuta el cálculo de penalidad de factor de potencia y recomendación de banco de capacitores."""
    result = controller.calcular_cos_fi(request)
    return APIResponseDTO[CalculoCosFiResponseDTO](success=True, data=result)
