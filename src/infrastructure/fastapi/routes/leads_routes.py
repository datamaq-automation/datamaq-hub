"""FastAPI routes for lead capture and automatic scheduling."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from src.adapters.controllers.dependencies import (
    get_default_calendar_gateway,
    get_default_contacts_gateway,
    get_default_lead_notifier_gateway,
    get_leads_controller,
)
from src.adapters.controllers.leads_controller import LeadsController
from src.application.dtos.leads_dto import IngestLeadDTO, IngestLeadResponseDTO
from src.infrastructure.pydantic.config import get_settings

router = APIRouter(prefix="/api/v1/leads", tags=["Leads & Webhooks"])


def get_configured_leads_controller() -> LeadsController:
    """Dependency resolver creating LeadsController with configured DB and Telegram credentials."""
    settings = get_settings()
    c_repo = get_default_contacts_gateway(database_url=settings.roundcube_db_url)
    cal_repo = get_default_calendar_gateway(database_url=settings.roundcube_db_url)
    notifier = get_default_lead_notifier_gateway(
        bot_token=settings.telegram_bot_token,
        chat_id=settings.telegram_chat_id,
    )
    return get_leads_controller(
        contacts_repo=c_repo,
        calendar_repo=cal_repo,
        notifier=notifier,
    )


@router.post(
    "/ingest",
    response_model=IngestLeadResponseDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Ingestar lead web o de anuncios",
    description="Registra automáticamente un nuevo prospecto en la libreta de Roundcube, crea un evento de agenda para seguimiento y notifica por Telegram.",
)
def ingestar_lead_endpoint(
    body: IngestLeadDTO,
    controller: Annotated[LeadsController, Depends(get_configured_leads_controller)],
) -> IngestLeadResponseDTO:
    """Ingests a commercial lead, creating contact and scheduling follow-up."""
    return controller.ingestar_lead(dto=body)
