"""Controller for lead capture and processing."""

from src.application.dtos.leads_dto import IngestLeadDTO, IngestLeadResponseDTO
from src.application.use_cases.ingestar_lead import IngestarLeadUseCase


class LeadsController:
    """Agnostic controller orchestrating lead ingestion operations."""

    def __init__(self, ingestar_lead_uc: IngestarLeadUseCase) -> None:
        self._ingestar_lead_uc = ingestar_lead_uc

    def ingestar_lead(self, dto: IngestLeadDTO) -> IngestLeadResponseDTO:
        return self._ingestar_lead_uc.execute(dto)
