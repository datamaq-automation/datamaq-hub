"""Caso de uso para consultar un recibo de sueldo por su identificador único."""

from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.recibos.exceptions import ReciboNotFoundError
from src.domain.recibos.ports import ReciboRepositoryPort


class ObtenerReciboUseCase:
    """Recupera un recibo persistido por su ID."""

    def __init__(self, repository: ReciboRepositoryPort) -> None:
        self._repository = repository

    def execute(self, id_recibo: str) -> ReceiptResponseDTO:
        recibo = self._repository.obtener_por_id(id_recibo)
        if not recibo:
            raise ReciboNotFoundError(
                f"Recibo de sueldo con ID '{id_recibo}' no encontrado."
            )
        return ReceiptMapper.to_dto(recibo)
