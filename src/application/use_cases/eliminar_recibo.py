"""Caso de uso para eliminar un recibo de sueldo persistido."""

from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.recibos.ports import ReciboRepositoryPort


class EliminarReciboUseCase:
    """Elimina físicamente un recibo de sueldo por su identificador."""

    def __init__(self, repository: ReciboRepositoryPort) -> None:
        self._repository = repository

    def execute(self, id_recibo: str) -> bool:
        eliminado = self._repository.eliminar(id_recibo)
        if not eliminado:
            raise ReciboNotFoundError(
                f"Recibo de sueldo con ID '{id_recibo}' no encontrado."
            )
        return True
