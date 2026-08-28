"""Rutas FastAPI para el subdominio de agenda y briefing unificado."""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from src.adapters.controllers.agenda_controller import AgendaController
from src.adapters.controllers.dependencies import get_agenda_controller
from src.application.dtos.briefing_dtos import BriefingDiarioResponseDTO
from src.application.dtos.common_dto import APIResponseDTO

router = APIRouter(prefix="/agenda", tags=["Agenda"])


@router.get(
    "/briefing",
    response_model=APIResponseDTO[BriefingDiarioResponseDTO],
    summary="Obtener el briefing diario unificado de clases, tareas y eventos",
    status_code=status.HTTP_200_OK,
)
def obtener_briefing_diario(
    cuit: Annotated[
        str,
        Query(
            description="CUIT del docente (con o sin guiones)",
            examples=["20365283924"],
        ),
    ],
    fecha: Annotated[
        date | None,
        Query(
            description="Fecha de consulta (YYYY-MM-DD). Si no se envía, usa la fecha actual",
            examples=["2026-08-28"],
        ),
    ] = None,
    controller: Annotated[AgendaController, Depends(get_agenda_controller)] = None,  # type: ignore
) -> APIResponseDTO[BriefingDiarioResponseDTO]:
    """Retorna el panorama completo del día con métricas, cronograma de clases, tareas prioritarias y texto formateado para Telegram."""
    return controller.obtener_briefing(docente_cuit=cuit, fecha=fecha)
