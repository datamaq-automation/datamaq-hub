"""Puertos del subdominio de tareas."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from src.domain.tareas.entities import Tarea
from src.domain.tareas.value_objects import (
    CategoriaTarea,
    EstadoTarea,
    PrioridadTarea,
)


@dataclass(frozen=True)
class FiltrosTarea:
    estado: EstadoTarea | None = None
    categoria: CategoriaTarea | None = None
    prioridad: PrioridadTarea | None = None
    docente_cuit: str | None = None
    id_referencia: str | None = None
    fecha_limite_desde: date | None = None
    fecha_limite_hasta: date | None = None
    limite: int | None = None
    offset: int | None = None


class TareaRepositoryPort(ABC):
    """Puerto de persistencia para el subdominio de tareas."""

    @abstractmethod
    def guardar(self, tarea: Tarea) -> Tarea:
        """Guarda una nueva tarea."""
        ...

    @abstractmethod
    def obtener_por_id(self, id_tarea: str) -> Tarea | None:
        """Obtiene una tarea por su ID."""
        ...

    @abstractmethod
    def listar(self, filtros: FiltrosTarea | None = None) -> list[Tarea]:
        """Lista tareas aplicando filtros opcionales."""
        ...

    @abstractmethod
    def actualizar(self, tarea: Tarea) -> Tarea:
        """Actualiza una tarea existente."""
        ...

    @abstractmethod
    def eliminar(self, id_tarea: str) -> bool:
        """Elimina una tarea por su ID."""
        ...
