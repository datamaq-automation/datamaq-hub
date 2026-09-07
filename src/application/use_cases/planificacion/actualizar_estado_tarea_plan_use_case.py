"""Use case for updating the state of a planning task and recalculating the Kanban board."""

from src.application.dtos.planificacion_dtos import TableroKanbanDTO
from src.application.mappers.planificacion_mapper import PlanificacionMapper
from src.domain.planificacion.exceptions import TareaPlanInvalidaError
from src.domain.planificacion.ports import PlanificacionRepositoryPort
from src.domain.planificacion.value_objects import EstadoTareaPlan


class ActualizarEstadoTareaPlanUseCase:
    """Caso de uso para mover una tarea entre columnas Kanban y recalcular métricas."""

    def __init__(self, repository: PlanificacionRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        id_tarea: str,
        nuevo_estado_str: str,
        id_plan: str = "vaca_muerta",
    ) -> TableroKanbanDTO:
        """Actualiza el estado de la tarea y retorna el tablero actualizado."""
        clean_estado = nuevo_estado_str.strip().upper()
        try:
            nuevo_estado = EstadoTareaPlan(clean_estado)
        except ValueError as exc:
            validos = [e.value for e in EstadoTareaPlan]
            raise TareaPlanInvalidaError(
                f"Estado inválido '{nuevo_estado_str}'. Estados válidos: {', '.join(validos)}"
            ) from exc

        tablero = self._repository.actualizar_estado_tarea(
            id_tarea=id_tarea,
            nuevo_estado=nuevo_estado,
            id_plan=id_plan,
        )
        return PlanificacionMapper.tablero_entidad_a_dto(tablero)
