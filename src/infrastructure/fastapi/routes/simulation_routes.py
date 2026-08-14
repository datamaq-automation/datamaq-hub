"""FastAPI routing for salary projection and simulation."""

from typing import Annotated

from fastapi import APIRouter, Depends

from src.adapters.controllers.dependencies import get_simulation_controller
from src.adapters.controllers.simulation_controller import SimulationController
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.simulation_dto import (
    SimulacionSueldoRequestDTO,
    SimulacionSueldoResponseDTO,
)

router = APIRouter(prefix="/simulacion", tags=["Simulacion"])


@router.post(
    "",
    response_model=APIResponseDTO[SimulacionSueldoResponseDTO],
    summary="Simulate / Project teacher salary",
    description=(
        "Calculates deterministic salary projection for DGCyE PBA teachers based on active positions, "
        "seniority, module count, and retroactive news."
    ),
    responses={
        200: {"description": "Salary simulation calculated successfully"},
        422: {"description": "Validation error in designation parameters"},
    },
)
async def simulate_salary(
    request: SimulacionSueldoRequestDTO,
    controller: Annotated[SimulationController, Depends(get_simulation_controller)],
) -> APIResponseDTO[SimulacionSueldoResponseDTO]:
    """Calculate projected teacher salary."""
    return controller.simulate(request)
