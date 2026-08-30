from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends

from src.adapters.controllers.dependencies import get_simulation_controller
from src.adapters.controllers.simulation_controller import SimulationController
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.simulation_dto import (
    SimulacionSueldoCuitResponseDTO,
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


@router.post(
    "/docente/{cuit}",
    response_model=APIResponseDTO[SimulacionSueldoCuitResponseDTO],
    summary="Project teacher salary dynamically by CUIT",
    description="Loads active positions from database and projects the teacher salary.",
    responses={
        200: {"description": "Salary simulation calculated successfully"},
        404: {"description": "Docente not found or has no active positions"},
    },
)
async def project_salary_by_cuit(
    cuit: str,
    controller: Annotated[SimulationController, Depends(get_simulation_controller)],
    periodo: str | None = None,
) -> APIResponseDTO[SimulacionSueldoCuitResponseDTO]:
    """Calculate projected teacher salary by CUIT."""
    if periodo is None:
        periodo = datetime.now().strftime("%Y%m")
    return controller.project_by_cuit(cuit, periodo)

