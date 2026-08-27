"""Use case for updating an existing calendar event."""

from src.application.dtos.calendar_dto import CalendarEventDTO, UpdateEventDTO
from src.application.mappers.calendar_mapper import CalendarMapper
from src.domain.calendar.entities import CalendarEvent
from src.domain.calendar.exceptions import EventNotFoundError
from src.domain.calendar.ports import CalendarRepositoryPort
from src.domain.calendar.value_objects import EventDateTimeInterval


class UpdateCalendarEventUseCase:
    """Use case to update event details and time bounds."""

    def __init__(self, repository: CalendarRepositoryPort) -> None:
        self.repository = repository

    def execute(
        self, event_id: str, dto: UpdateEventDTO, account: str
    ) -> CalendarEventDTO:
        existing = self.repository.get_event_by_id(event_id=event_id, account=account)
        if not existing:
            raise EventNotFoundError(event_id=event_id, account=account)

        inicio = dto.inicio if dto.inicio is not None else existing.inicio
        fin = dto.fin if dto.fin is not None else existing.fin

        # Validate interval
        EventDateTimeInterval(inicio=inicio, fin=fin)

        titulo = dto.titulo.strip() if dto.titulo is not None else existing.titulo
        descripcion = (
            dto.descripcion.strip()
            if dto.descripcion is not None
            else existing.descripcion
        )
        ubicacion = (
            dto.ubicacion.strip() if dto.ubicacion is not None else existing.ubicacion
        )
        todo_el_dia = (
            dto.todo_el_dia if dto.todo_el_dia is not None else existing.todo_el_dia
        )
        estado = (
            dto.estado.strip().upper() if dto.estado is not None else existing.estado
        )
        asistentes = (
            list(dto.asistentes) if dto.asistentes is not None else existing.asistentes
        )
        url = dto.url.strip() if dto.url is not None else existing.url
        categorias = (
            dto.categorias.strip()
            if dto.categorias is not None
            else existing.categorias
        )

        updated_event = CalendarEvent(
            id_evento=existing.id_evento,
            id_calendario=existing.id_calendario,
            uid=existing.uid,
            titulo=titulo,
            inicio=inicio,
            fin=fin,
            descripcion=descripcion,
            ubicacion=ubicacion,
            todo_el_dia=todo_el_dia,
            estado=estado,
            asistentes=asistentes,
            url=url,
            categorias=categorias,
            cuenta=existing.cuenta,
        )

        saved = self.repository.update_event(event=updated_event, account=account)
        return CalendarMapper.to_event_dto(saved)
