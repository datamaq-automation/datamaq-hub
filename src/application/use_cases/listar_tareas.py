"""Caso de uso para listar tareas con filtros."""

from src.application.dtos.tarea_dtos import ListarTareasResponseDTO
from src.application.mappers.tarea_mapper import TareaMapper
from src.domain.tareas.ports import FiltrosTarea, TareaRepositoryPort


class ListarTareasUseCase:
    """Lista tareas aplicando filtros opcionales de búsqueda y paginación."""

    def __init__(self, repository: TareaRepositoryPort) -> None:
        self._repository = repository

    def execute(self, filtros: FiltrosTarea | None = None) -> ListarTareasResponseDTO:
        tareas_domain = self._repository.listar(filtros)
        dtos = [TareaMapper.to_dto(t) for t in tareas_domain]
        return ListarTareasResponseDTO(total=len(dtos), tareas=dtos)
