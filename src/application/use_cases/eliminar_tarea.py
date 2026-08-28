"""Caso de uso para eliminar una tarea por su ID."""

from src.domain.tareas.exceptions import TareaNoEncontradaException
from src.domain.tareas.ports import TareaRepositoryPort


class EliminarTareaUseCase:
    """Elimina una tarea del sistema."""

    def __init__(self, repository: TareaRepositoryPort) -> None:
        self._repository = repository

    def execute(self, id_tarea: str) -> bool:
        eliminado = self._repository.eliminar(id_tarea)
        if not eliminado:
            raise TareaNoEncontradaException(
                f"No se encontró la tarea con ID '{id_tarea}'."
            )
        return True
