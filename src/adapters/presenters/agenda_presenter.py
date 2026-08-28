"""Presenter para el subdominio de agenda y briefing unificado."""

from src.application.dtos.briefing_dtos import BriefingDiarioResponseDTO
from src.application.dtos.common_dto import APIResponseDTO


class AgendaPresenter:
    """Formatea la respuesta del Briefing Diario en la envolvente estándar de API."""

    @staticmethod
    def present_briefing(
        dto: BriefingDiarioResponseDTO,
    ) -> APIResponseDTO[BriefingDiarioResponseDTO]:
        return APIResponseDTO(success=True, data=dto)
