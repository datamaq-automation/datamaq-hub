"""Controlador de resúmenes de tarjetas de crédito (agnóstico de transporte)."""

from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.tarjeta_dto import ResumenTarjetaDTO
from src.application.use_cases.procesar_resumen_tarjeta import (
    ProcesarResumenTarjetaUseCase,
)


class TarjetaController:
    """Maneja la carga y procesamiento de resúmenes de tarjeta de crédito."""

    def __init__(self, procesar_use_case: ProcesarResumenTarjetaUseCase) -> None:
        self._procesar_use_case = procesar_use_case

    def cargar_resumen(self, pdf_bytes: bytes) -> APIResponseDTO[ResumenTarjetaDTO]:
        """Procesa un PDF de tarjeta y devuelve el resumen persistido."""
        resultado = self._procesar_use_case.execute(pdf_bytes)
        return APIResponseDTO(success=True, data=resultado)
