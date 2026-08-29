from typing import Any

from src.adapters.presenters.receipt_presenter import ReceiptPresenter
from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.conciliacion_dto import ConciliacionResponseDTO
from src.application.dtos.horarios_docencia_dto import DesignacionDocenteDTO
from src.application.dtos.receipt_dto import ReceiptResponseDTO, ReceiptSummaryDTO
from src.application.mappers.receipt_mapper import ReceiptMapper
from src.application.use_cases.conciliar_recibo import ConciliarReciboUseCase
from src.application.use_cases.crear_designaciones_desde_recibo import (
    CrearDesignacionesDesdeReciboUseCase,
)
from src.application.use_cases.eliminar_recibo import EliminarReciboUseCase
from src.application.use_cases.listar_recibos import ListarRecibosUseCase
from src.application.use_cases.obtener_recibo import ObtenerReciboUseCase
from src.application.use_cases.parse_receipt import ParseReceiptUseCase


class ReceiptController:
    """Handles receipt parsing, persistence and reconciliation operations independently of web transport."""

    def __init__(
        self,
        parse_use_case: ParseReceiptUseCase,
        obtener_use_case: ObtenerReciboUseCase | None = None,
        listar_use_case: ListarRecibosUseCase | None = None,
        eliminar_use_case: EliminarReciboUseCase | None = None,
        conciliar_use_case: ConciliarReciboUseCase | None = None,
        crear_desde_recibo_use_case: CrearDesignacionesDesdeReciboUseCase | None = None,
    ) -> None:
        self._parse_use_case = parse_use_case
        self._obtener_use_case = obtener_use_case
        self._listar_use_case = listar_use_case
        self._eliminar_use_case = eliminar_use_case
        self._conciliar_use_case = conciliar_use_case
        self._crear_desde_recibo_use_case = crear_desde_recibo_use_case

    def parse_bytes(
        self,
        content: bytes,
        filename: str = "receipt.pdf",
        persistir: bool = True,
        solo_resumen: bool = False,
    ) -> APIResponseDTO[ReceiptResponseDTO] | APIResponseDTO[ReceiptSummaryDTO]:
        """Execute receipt parsing on byte stream and present envelope."""
        receipt_dto = self._parse_use_case.execute_bytes(
            content, filename=filename, persistir=persistir
        )
        if solo_resumen:
            return APIResponseDTO[ReceiptSummaryDTO](
                success=True, data=ReceiptMapper.to_summary(receipt_dto)
            )
        return ReceiptPresenter.present(receipt_dto)

    def obtener_por_id(self, id_recibo: str) -> APIResponseDTO[ReceiptResponseDTO]:
        """Recupera un recibo persistido por su identificador."""
        if not self._obtener_use_case:
            raise RuntimeError("ObtenerReciboUseCase no configurado.")
        dto = self._obtener_use_case.execute(id_recibo)
        return ReceiptPresenter.present(dto)

    def listar(
        self,
        cuit: str | None = None,
        mes_pago: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> APIResponseDTO[list[ReceiptResponseDTO]]:
        """Lista recibos de sueldo persistidos con paginación y filtros."""
        if not self._listar_use_case:
            raise RuntimeError("ListarRecibosUseCase no configurado.")
        dtos = self._listar_use_case.execute(
            cuit=cuit, mes_pago=mes_pago, limit=limit, offset=offset
        )
        return APIResponseDTO(success=True, data=dtos)

    def eliminar(self, id_recibo: str) -> APIResponseDTO[dict[str, Any]]:
        """Elimina un recibo persistido."""
        if not self._eliminar_use_case:
            raise RuntimeError("EliminarReciboUseCase no configurado.")
        self._eliminar_use_case.execute(id_recibo)
        return APIResponseDTO(
            success=True, data={"eliminado": True, "id_recibo": id_recibo}
        )

    def conciliar(self, id_recibo: str) -> APIResponseDTO[ConciliacionResponseDTO]:
        """Ejecuta la conciliación automática entre el recibo y las designaciones del docente."""
        if not self._conciliar_use_case:
            raise RuntimeError("ConciliarReciboUseCase no configurado.")
        resultado_dto = self._conciliar_use_case.execute(id_recibo)
        return APIResponseDTO(success=True, data=resultado_dto)

    def crear_designaciones_huerfanas(
        self,
        id_recibo: str,
        secuencias: list[str] | None = None,
    ) -> APIResponseDTO[list[DesignacionDocenteDTO]]:
        """Auto-genera designaciones históricas a partir de las líneas no registradas del recibo."""
        if not self._crear_desde_recibo_use_case:
            raise RuntimeError("CrearDesignacionesDesdeReciboUseCase no configurado.")
        creadas = self._crear_desde_recibo_use_case.execute(
            id_recibo=id_recibo, secuencias=secuencias
        )
        return APIResponseDTO(success=True, data=creadas)
