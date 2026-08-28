"""Port protocols for lead notifications and persistence."""

from typing import Protocol

from src.domain.leads.entities import Lead


class LeadNotifierPort(Protocol):
    """Port for dispatching immediate notifications upon new lead ingestion."""

    def notificar_nuevo_lead(self, lead: Lead) -> bool:
        """Sends a notification to designated channels (Telegram, Email, etc.)."""
        ...
