from src.adapters.presenters.simulation_presenter import SimulationPresenter
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.simulation_dto import (
    SimulacionSueldoCuitResponseDTO,
    SimulacionSueldoRequestDTO,
    SimulacionSueldoResponseDTO,
)
from src.application.use_cases.project_salary import ProjectSalaryUseCase
from src.application.use_cases.proyectar_sueldo_docente_vigente import (
    ProyectarSueldoDocenteVigenteUseCase,
)


class SimulationController:
    """Handles salary simulation operations independently of web transport."""

    def __init__(
        self,
        project_use_case: ProjectSalaryUseCase,
        project_by_cuit_use_case: ProyectarSueldoDocenteVigenteUseCase,
    ) -> None:
        self._project_use_case = project_use_case
        self._project_by_cuit_use_case = project_by_cuit_use_case

    def simulate(
        self, request: SimulacionSueldoRequestDTO
    ) -> APIResponseDTO[SimulacionSueldoResponseDTO]:
        """Execute salary projection and present response envelope."""
        resultado_dto = self._project_use_case.execute(request)
        return SimulationPresenter.present(resultado_dto)

    def project_by_cuit(
        self, cuit: str, periodo: str
    ) -> APIResponseDTO[SimulacionSueldoCuitResponseDTO]:
        """Execute salary projection based on active positions by CUIT."""
        resultado_dto = self._project_by_cuit_use_case.execute(cuit, periodo)
        return SimulationPresenter.present_cuit(resultado_dto)

