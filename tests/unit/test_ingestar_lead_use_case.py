"""Unit tests for IngestarLeadUseCase."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.application.dtos.leads_dto import IngestLeadDTO
from src.application.use_cases.ingestar_lead import IngestarLeadUseCase
from src.domain.calendar.entities import Calendar, CalendarEvent
from src.domain.contacts.entities import Contact


def test_ingestar_lead_full_flow():
    # Setup mocks
    contacts_repo = MagicMock()
    calendar_repo = MagicMock()
    notifier = MagicMock()

    contacts_repo.create_contact.return_value = Contact(
        id_contacto="c-123",
        nombre="Carlos Benítez",
        email="carlos@plasticos.com.ar",
        telefono="+5491133332222",
    )

    calendar_repo.get_or_create_default_calendar.return_value = Calendar(
        id_calendario="cal-1",
        nombre="Default",
    )
    now_utc = datetime.now(timezone.utc)
    calendar_repo.create_event.return_value = CalendarEvent(
        id_evento="evt-456",
        id_calendario="cal-1",
        titulo="📞 Seguimiento: Carlos Benítez (Plásticos Norte)",
        inicio=now_utc,
        fin=now_utc,
    )

    use_case = IngestarLeadUseCase(
        contacts_repo=contacts_repo,
        calendar_repo=calendar_repo,
        notifier=notifier,
    )

    dto = IngestLeadDTO(
        nombre="Carlos Benítez",
        email="carlos@plasticos.com.ar",
        telefono="+5491133332222",
        empresa="Plásticos Norte S.A.",
        mensaje="Necesito cotización de banco de capacitores.",
        fuente="landing_energia",
        utm_campaign="cero_multas",
    )

    result = use_case.execute(dto)

    assert result.success is True
    assert result.id_contacto == "c-123"
    assert result.id_evento_seguimiento == "evt-456"

    # Verify calls
    assert contacts_repo.create_contact.called
    assert calendar_repo.create_event.called
    assert notifier.notificar_nuevo_lead.called
