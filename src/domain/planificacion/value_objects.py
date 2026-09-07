"""Value objects for planificacion bounded context."""

from enum import Enum


class EstadoTareaPlan(str, Enum):
    """Estados kanban de una tarea en el plan."""

    PENDIENTE = "PENDIENTE"
    EN_PROCESO = "EN_PROCESO"
    COMPLETADA = "COMPLETADA"
