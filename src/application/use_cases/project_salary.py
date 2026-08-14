"""Use case for calculating and projecting teacher salaries deterministically."""

from src.application.dtos.simulation_dto import (
    SimulacionSueldoRequestDTO,
    SimulacionSueldoResponseDTO,
)
from src.application.mappers.simulation_mapper import SimulationMapper
from src.domain.liquidacion.ports import ParitariaRepositoryPort
from src.domain.liquidacion.services import MotorLiquidacionDocenteService
from src.domain.liquidacion.value_objects import ParametrosParitaria


class ProjectSalaryUseCase:
    """Orchestrates deterministic salary projection based on active positions and news."""

    def __init__(
        self,
        paritaria_repo: ParitariaRepositoryPort,
        motor: MotorLiquidacionDocenteService | None = None,
    ) -> None:
        self._paritaria_repo = paritaria_repo
        self._motor = motor or MotorLiquidacionDocenteService()

    def execute(
        self,
        request: SimulacionSueldoRequestDTO,
        paritaria: ParametrosParitaria | None = None,
    ) -> SimulacionSueldoResponseDTO:
        """Execute salary projection for given designations and seniority."""
        if paritaria is None:
            paritaria = self._paritaria_repo.obtener_por_periodo(
                request.periodo_proyectado
            )

        domain_designaciones = [
            SimulationMapper.to_domain_designacion(
                d, periodo_por_defecto=request.periodo_proyectado
            )
            for d in request.designaciones
        ]

        resultado_consolidado = self._motor.liquidar_consolidado(
            designaciones=domain_designaciones,
            anios_antiguedad=request.anios_antiguedad,
            paritaria=paritaria,
            periodo_proyectado=request.periodo_proyectado,
            tope_bonificaciones_modulos=request.tope_bonificaciones_modulos,
        )

        return SimulationMapper.to_dto(resultado_consolidado)
