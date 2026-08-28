"""Presenter para formatear respuestas del subdominio de tareas."""

from typing import Any

from src.application.dtos.common_dto import APIResponseDTO
from src.application.dtos.tarea_dtos import (
    GenerarTareasReciboResponseDTO,
    ListarTareasResponseDTO,
    TareaResponseDTO,
)


class TareaPresenter:
    """Formatea DTOs de tareas en envolventes de respuesta estándar."""

    @staticmethod
    def present_tarea(dto: TareaResponseDTO) -> APIResponseDTO[TareaResponseDTO]:
        return APIResponseDTO(success=True, data=dto)

    @staticmethod
    def present_listado(
        dto: ListarTareasResponseDTO,
    ) -> APIResponseDTO[ListarTareasResponseDTO]:
        return APIResponseDTO(success=True, data=dto)

    @staticmethod
    def present_generadas(
        dto: GenerarTareasReciboResponseDTO,
    ) -> APIResponseDTO[GenerarTareasReciboResponseDTO]:
        return APIResponseDTO(success=True, data=dto)

    @staticmethod
    def present_eliminacion(id_tarea: str) -> APIResponseDTO[dict[str, Any]]:
        return APIResponseDTO(
            success=True, data={"eliminado": True, "id_tarea": id_tarea}
        )
