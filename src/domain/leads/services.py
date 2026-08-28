"""Domain services for lead validation and formatting."""

from src.domain.leads.entities import Lead
from src.domain.leads.exceptions import LeadValidationException


class LeadValidationService:
    """Pure domain service for validating incoming lead payloads."""

    @staticmethod
    def validate_lead(lead: Lead) -> None:
        """Validates that lead has at least a valid name and contact method (email or phone)."""
        if not lead.nombre or not lead.nombre.strip():
            raise LeadValidationException("El nombre del lead es obligatorio.")
        if (not lead.email or not lead.email.strip()) and (
            not lead.telefono or not lead.telefono.strip()
        ):
            raise LeadValidationException(
                "Debe proporcionar al menos un medio de contacto (email o teléfono)."
            )
