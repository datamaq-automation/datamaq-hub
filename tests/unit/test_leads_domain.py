"""Unit tests for leads domain entities and validation service."""

import pytest

from src.domain.leads.entities import Lead
from src.domain.leads.exceptions import LeadValidationException
from src.domain.leads.services import LeadValidationService


def test_lead_validation_success():
    lead = Lead(
        id_lead="123",
        nombre="Juan Pérez",
        email="juan@empresa.com",
        telefono="+54 9 11 1234-5678",
        empresa="Empresa Industrial S.A.",
    )
    # Should not raise exception
    LeadValidationService.validate_lead(lead)


def test_lead_validation_missing_name():
    lead = Lead(
        id_lead="123",
        nombre="",
        email="juan@empresa.com",
    )
    with pytest.raises(
        LeadValidationException, match="El nombre del lead es obligatorio."
    ):
        LeadValidationService.validate_lead(lead)


def test_lead_validation_missing_contact_method():
    lead = Lead(
        id_lead="123",
        nombre="Juan Pérez",
        email="",
        telefono="",
    )
    with pytest.raises(LeadValidationException, match="al menos un medio de contacto"):
        LeadValidationService.validate_lead(lead)
