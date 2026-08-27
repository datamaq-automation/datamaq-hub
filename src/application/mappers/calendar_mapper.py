"""Mapper between CalendarEvent domain entities and Pydantic DTOs."""

from src.application.dtos.calendar_dto import CalendarEventDTO, TimeSlotDTO
from src.domain.calendar.entities import CalendarEvent, TimeSlot


class CalendarMapper:
    """Static mapper for calendar events and availability slots."""

    @staticmethod
    def to_event_dto(entity: CalendarEvent) -> CalendarEventDTO:
        return CalendarEventDTO(
            id_evento=entity.id_evento,
            id_calendario=entity.id_calendario,
            uid=entity.uid,
            titulo=entity.titulo,
            inicio=entity.inicio,
            fin=entity.fin,
            descripcion=entity.descripcion,
            ubicacion=entity.ubicacion,
            todo_el_dia=entity.todo_el_dia,
            estado=entity.estado,
            asistentes=list(entity.asistentes),
            url=entity.url,
            categorias=entity.categorias,
            cuenta=entity.cuenta,
        )

    @staticmethod
    def to_slot_dto(slot: TimeSlot) -> TimeSlotDTO:
        return TimeSlotDTO(
            inicio=slot.inicio,
            fin=slot.fin,
            disponible=slot.disponible,
            motivo=slot.motivo,
        )
