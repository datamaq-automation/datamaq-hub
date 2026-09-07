"""Controller for planificacion and Kanban/PERT board operations."""

from src.application.dtos.planificacion_dtos import TableroKanbanDTO
from src.application.use_cases.planificacion.actualizar_estado_tarea_plan_use_case import (
    ActualizarEstadoTareaPlanUseCase,
)
from src.application.use_cases.planificacion.obtener_tablero_kanban_pert_use_case import (
    ObtenerTableroKanbanPertUseCase,
)


class PlanificacionController:
    """Controlador agnóstico de transporte para consultar y actualizar el tablero Kanban y red PERT."""

    def __init__(
        self,
        obtener_tablero_uc: ObtenerTableroKanbanPertUseCase,
        actualizar_estado_uc: ActualizarEstadoTareaPlanUseCase,
    ) -> None:
        self._obtener_tablero_uc = obtener_tablero_uc
        self._actualizar_estado_uc = actualizar_estado_uc

    def obtener_tablero(self, id_plan: str = "vaca_muerta") -> TableroKanbanDTO:
        """Obtiene el tablero Kanban con cálculos PERT-CPM para el plan dado."""
        return self._obtener_tablero_uc.execute(id_plan=id_plan)

    def actualizar_estado_tarea(
        self,
        id_tarea: str,
        nuevo_estado: str,
        id_plan: str = "vaca_muerta",
    ) -> TableroKanbanDTO:
        """Actualiza el estado de una tarea y retorna el tablero recalculado."""
        return self._actualizar_estado_uc.execute(
            id_tarea=id_tarea,
            nuevo_estado_str=nuevo_estado,
            id_plan=id_plan,
        )
