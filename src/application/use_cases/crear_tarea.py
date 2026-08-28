"""Caso de uso para crear una nueva tarea."""

from src.application.dtos.tarea_dtos import CrearTareaDTO, TareaResponseDTO
from src.application.mappers.tarea_mapper import TareaMapper
from src.domain.tareas.ports import TareaRepositoryPort


class CrearTareaUseCase:
    """Caso de uso que orquesta la creación y persistencia de una tarea."""

    def __init__(self, repository: TareaRepositoryPort) -> None:
        self._repository = repository

    def execute(self, dto: CrearTareaDTO) -> TareaResponseDTO:
        tarea_domain = TareaMapper.to_domain_from_create(dto)
        guardada = self._repository.guardar(tarea_domain)
        return TareaMapper.to_dto(guardada)
