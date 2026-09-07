"""Use case for retrieving the Kanban board with calculated PERT-CPM network metrics."""

from src.application.dtos.planificacion_dtos import TableroKanbanDTO
from src.application.mappers.planificacion_mapper import PlanificacionMapper
from src.domain.planificacion.ports import PlanificacionRepositoryPort


class ObtenerTableroKanbanPertUseCase:
    """Caso de uso para consultar el tablero Kanban y red PERT-CPM de un plan."""

    def __init__(self, repository: PlanificacionRepositoryPort) -> None:
        self._repository = repository

    def execute(self, id_plan: str = "vaca_muerta") -> TableroKanbanDTO:
        """Obtiene y calcula el tablero Kanban para el plan especificado."""
        tablero = self._repository.obtener_tablero(id_plan=id_plan)
        return PlanificacionMapper.tablero_entidad_a_dto(tablero)
