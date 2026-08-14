"""Pure transport-agnostic controller for salary simulation."""

from src.adapters.presenters.simulation_presenter import SimulationPresenter
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.simulation_dto import (
    SimulacionSueldoRequestDTO,
    SimulacionSueldoResponseDTO,
)
from src.application.use_cases.project_salary import ProjectSalaryUseCase


class SimulationController:
    """Handles salary simulation operations independently of web transport."""

    def __init__(self, project_use_case: ProjectSalaryUseCase) -> None:
        self._project_use_case = project_use_case

    def simulate(
        self, request: SimulacionSueldoRequestDTO
    ) -> APIResponseDTO[SimulacionSueldoResponseDTO]:
        """Execute salary projection and present response envelope."""
        resultado_dto = self._project_use_case.execute(request)
        return SimulationPresenter.present(resultado_dto)
