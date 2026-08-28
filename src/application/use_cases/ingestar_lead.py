"""Use case for ingesting and auto-scheduling leads from web and advertising forms."""

import logging
import uuid
from datetime import datetime, timedelta, timezone

from src.application.dtos.leads_dto import IngestLeadDTO, IngestLeadResponseDTO
from src.domain.calendar.entities import CalendarEvent
from src.domain.calendar.ports import CalendarRepositoryPort
from src.domain.contacts.entities import Contact
from src.domain.contacts.ports import ContactsRepositoryPort
from src.domain.contacts.services import VCardFormatterService
from src.domain.leads.entities import Lead
from src.domain.leads.ports import LeadNotifierPort
from src.domain.leads.services import LeadValidationService
from src.domain.leads.value_objects import LeadSourceInfo, LeadStatus

logger = logging.getLogger(__name__)


class IngestarLeadUseCase:
    """Orchestrates validation, contact creation, calendar follow-up scheduling and notification."""

    def __init__(
        self,
        contacts_repo: ContactsRepositoryPort,
        calendar_repo: CalendarRepositoryPort | None = None,
        notifier: LeadNotifierPort | None = None,
    ) -> None:
        self._contacts_repo = contacts_repo
        self._calendar_repo = calendar_repo
        self._notifier = notifier

    def execute(self, dto: IngestLeadDTO) -> IngestLeadResponseDTO:
        account = (dto.cuenta or "").strip()

        # 1. Crear y validar entidad Lead
        lead = Lead(
            id_lead=str(uuid.uuid4()),
            nombre=dto.nombre.strip(),
            email=dto.email.strip(),
            telefono=dto.telefono.strip(),
            empresa=dto.empresa.strip(),
            mensaje=dto.mensaje.strip(),
            fuente=LeadSourceInfo(
                channel=dto.fuente,
                campaign=dto.utm_campaign,
            ),
            estado=LeadStatus.NUEVO,
            fecha_creacion=datetime.now(timezone.utc).isoformat(),
        )
        LeadValidationService.validate_lead(lead)

        # 2. Persistir contacto en Libreta de Roundcube
        note_text = (
            f"Lead Web [{dto.fuente}]"
            + (f" Campaña: {dto.utm_campaign}" if dto.utm_campaign else "")
            + (f"\nMensaje: {dto.mensaje}" if dto.mensaje else "")
        )
        vcard_text = VCardFormatterService.generate_vcard(
            name=lead.nombre,
            email=lead.email,
            phone=lead.telefono,
            organization=lead.empresa,
            note=note_text,
        )

        contact_entity = Contact(
            id_contacto="",
            nombre=lead.nombre,
            email=lead.email,
            telefono=lead.telefono,
            organizacion=lead.empresa,
            notas=note_text,
            vcard=vcard_text,
            cuenta=account,
        )
        created_contact = self._contacts_repo.create_contact(contact_entity, account)

        # 3. Crear evento de seguimiento en Agenda de OpenClaw (+1 día hábil a las 10:00)
        id_evento = ""
        if self._calendar_repo:
            cal = self._calendar_repo.get_or_create_default_calendar(account)
            now = datetime.now(timezone.utc)
            # Programar para mañana a las 10:00 AM (o lunes si es viernes/sábado)
            target_date = now + timedelta(days=1)
            if target_date.weekday() == 5:  # Sábado -> Lunes
                target_date += timedelta(days=2)
            elif target_date.weekday() == 6:  # Domingo -> Lunes
                target_date += timedelta(days=1)

            start_dt = target_date.replace(hour=10, minute=0, second=0, microsecond=0)
            end_dt = start_dt + timedelta(minutes=45)

            event = CalendarEvent(
                id_evento="",
                id_calendario=cal.id_calendario,
                titulo=f"📞 Seguimiento: {lead.nombre}"
                + (f" ({lead.empresa})" if lead.empresa else ""),
                inicio=start_dt,
                fin=end_dt,
                descripcion=(
                    f"Lead comercial entrante desde {dto.fuente}.\n"
                    f"Teléfono: {lead.telefono}\n"
                    f"Email: {lead.email}\n"
                    f"Empresa: {lead.empresa}\n"
                    f"Consulta: {lead.mensaje}"
                ),
                ubicacion="Llamada / WhatsApp",
                categorias="Comercial,Leads",
                cuenta=account,
            )
            created_event = self._calendar_repo.create_event(event, account)
            id_evento = created_event.id_evento

        # 4. Notificar a canales externos (Telegram Bot, etc.)
        if self._notifier:
            try:
                self._notifier.notificar_nuevo_lead(lead)
            except (ValueError, RuntimeError, OSError, TimeoutError) as exc:
                logger.warning(
                    "Fallo al notificar nuevo lead al canal externo: %s", exc
                )

        return IngestLeadResponseDTO(
            success=True,
            id_contacto=created_contact.id_contacto,
            id_evento_seguimiento=id_evento,
            mensaje=f"Lead '{lead.nombre}' registrado en libreta y agendado para seguimiento.",
        )
