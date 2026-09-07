"""Port interfaces for planificacion bounded context."""

from typing import Protocol

from src.domain.planificacion.entities import TableroKanban
from src.domain.planificacion.value_objects import EstadoTareaPlan


class PlanificacionRepositoryPort(Protocol):
    """Puerto para persistencia y lectura de planes y tareas de proyecto."""

    def obtener_tablero(self, id_plan: str = "vaca_muerta") -> TableroKanban:
        """Carga y retorna el tablero Kanban con cálculos PERT-CPM actualizados."""
        ...

    def actualizar_estado_tarea(
        self,
        id_tarea: str,
        nuevo_estado: EstadoTareaPlan,
        id_plan: str = "vaca_muerta",
    ) -> TableroKanban:
        """Actualiza el estado de una tarea y retorna el tablero Kanban recalculado."""
        ...
