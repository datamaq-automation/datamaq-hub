"""Caso de uso para marcar una tarea como completada."""

from src.application.dtos.tarea_dtos import TareaResponseDTO
from src.application.mappers.tarea_mapper import TareaMapper
from src.domain.tareas.exceptions import TareaNoEncontradaException
from src.domain.tareas.ports import TareaRepositoryPort


class CompletarTareaUseCase:
    """Marca una tarea como COMPLETADA y estampa la fecha de finalización."""

    def __init__(self, repository: TareaRepositoryPort) -> None:
        self._repository = repository

    def execute(self, id_tarea: str) -> TareaResponseDTO:
        tarea = self._repository.obtener_por_id(id_tarea)
        if not tarea:
            raise TareaNoEncontradaException(
                f"No se encontró la tarea con ID '{id_tarea}'."
            )

        completada = tarea.completar()
        guardada = self._repository.actualizar(completada)
        return TareaMapper.to_dto(guardada)
