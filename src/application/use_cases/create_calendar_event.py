"""Use case for creating a new calendar event."""

import uuid

from src.application.dtos.calendar_dto import CalendarEventDTO, CreateEventDTO
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.entities import CalendarEvent
from src.domain.calendar.ports import CalendarRepositoryPort
from src.domain.calendar.value_objects import EventDateTimeInterval


class CreateCalendarEventUseCase:
    """Use case to create and persist a new appointment or event."""

    def __init__(self, repository: CalendarRepositoryPort) -> None:
        self.repository = repository

    def execute(self, dto: CreateEventDTO, account: str) -> CalendarEventDTO:
        effective_account = dto.cuenta or account

        # Validate interval
        EventDateTimeInterval(inicio=dto.inicio, fin=dto.fin)

        calendar = self.repository.get_or_create_default_calendar(
            account=effective_account
        )

        event_uid = str(uuid.uuid4())
        event = CalendarEvent(
            id_evento="",
            id_calendario=calendar.id_calendario,
            uid=event_uid,
            titulo=dto.titulo.strip(),
            inicio=dto.inicio,
            fin=dto.fin,
            descripcion=dto.descripcion.strip(),
            ubicacion=dto.ubicacion.strip(),
            todo_el_dia=dto.todo_el_dia,
            estado="CONFIRMED",
            asistentes=list(dto.asistentes),
            url=dto.url.strip(),
            categorias=dto.categorias.strip(),
            cuenta=effective_account,
        )

        created = self.repository.create_event(event=event, account=effective_account)
        return CalendarMapper.to_event_dto(created)
