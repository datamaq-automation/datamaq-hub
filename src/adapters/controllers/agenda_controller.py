"""Controlador agnóstico de transporte para el subdominio de agenda y briefing diario."""

from datetime import date

from src.adapters.presenters.agenda_presenter import AgendaPresenter
from src.application.dtos.briefing_dtos import BriefingDiarioResponseDTO
from src.application.dtos.common_dto import APIResponseDTO
from src.application.use_cases.obtener_briefing_diario import (
    ObtenerBriefingDiarioUseCase,
)


class AgendaController:
    """Controlador que orquesta la generación del briefing diario."""

    def __init__(
        self,
        obtener_briefing_use_case: ObtenerBriefingDiarioUseCase,
    ) -> None:
        self._obtener_briefing_use_case = obtener_briefing_use_case

    def obtener_briefing(
        self,
        docente_cuit: str,
        fecha: date | None = None,
    ) -> APIResponseDTO[BriefingDiarioResponseDTO]:
        """Obtiene el briefing diario consolidado para un docente."""
        dto = self._obtener_briefing_use_case.execute(
            docente_cuit=docente_cuit,
            fecha=fecha,
        )
        return AgendaPresenter.present_briefing(dto)
