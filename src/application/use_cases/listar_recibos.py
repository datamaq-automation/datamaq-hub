"""Caso de uso para listar y filtrar recibos de sueldo persistidos."""

from src.application.dtos.receipt_dto import ReceiptResponseDTO
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.domain.recibos.ports import ReciboRepositoryPort


class ListarRecibosUseCase:
    """Orquesta el listado paginado de recibos de sueldo con filtros."""

    def __init__(self, repository: ReciboRepositoryPort) -> None:
        self._repository = repository

    def execute(
        self,
        cuit: str | None = None,
        mes_pago: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ReceiptResponseDTO]:
        recibos = self._repository.listar(
            cuit=cuit,
            mes_pago=mes_pago,
            limit=limit,
            offset=offset,
        )
        return [ReceiptMapper.to_dto(r) for r in recibos]
